import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "agent-discover.py"
SPEC = importlib.util.spec_from_file_location("easyproject_agent_discover", MODULE_PATH)
discovery = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(discovery)


class AgentDiscoveryTests(unittest.TestCase):
    def make_repo(self, root):
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)

    def test_emits_read_only_candidates_from_tracked_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            source = root / "src" / "sample.py"
            source.parent.mkdir()
            source.write_text("# TODO: revisit parser\n# FIXME: handle empty input\n", encoding="utf-8")
            (root / "untracked.py").write_text("# TODO: should not appear\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "src/sample.py"], check=True)

            report = discovery.discover(root)
            self.assertEqual(report["candidate_count"], 2)
            self.assertEqual(report["mode"], "read-only-review-candidates")
            self.assertFalse(report["safety"]["agents_executed"])
            self.assertFalse(report["safety"]["repository_write_permission"])
            self.assertTrue(report["safety"]["human_review_required"])
            schema = __import__("json").loads(
                (ROOT / ".ai/runtime/schemas/task.schema.json").read_text(encoding="utf-8")
            )
            for candidate in report["candidates"]:
                Draft202012Validator(schema).validate(candidate["task"])
                self.assertFalse(candidate["task"]["permissions"]["repository_write"])
                self.assertFalse(candidate["task"]["permissions"]["network_access"])
                self.assertEqual(candidate["task"]["risk"], "low")
            first = report["candidates"][0]
            self.assertEqual(first["evidence"]["path"], "src/sample.py")
            self.assertIn(first["evidence"]["marker"], {"TODO", "FIXME"})

    def test_candidate_ids_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            (root / "sample.py").write_text("# TODO follow up\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "sample.py"], check=True)
            one = discovery.discover(root)
            two = discovery.discover(root)
            self.assertEqual(one["candidates"], two["candidates"])

    def test_ignores_binary_and_oversized_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            (root / "binary.py").write_bytes(b"TODO\0FIXME")
            (root / "large.py").write_bytes(b"x" * (discovery.MAX_FILE_BYTES + 1))
            subprocess.run(["git", "-C", str(root), "add", "binary.py", "large.py"], check=True)
            report = discovery.discover(root)
            self.assertEqual(report["candidate_count"], 0)
            self.assertEqual(report["skipped_files"], 2)

    def test_ignores_documentation_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            (root / "guide.md").write_text("TODO in a documentation example\n", encoding="utf-8")
            (root / "sample.py").write_text("# TODO in source\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "guide.md", "sample.py"], check=True)
            report = discovery.discover(root)
            self.assertEqual(report["candidate_count"], 1)
            self.assertEqual(report["candidates"][0]["evidence"]["path"], "sample.py")
            self.assertEqual(report["skipped_files"], 1)

    def test_ignores_marker_vocabulary_definitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            source = root / "src" / "vocabulary.py"
            source.parent.mkdir()
            source.write_text(
                'MARKERS = {"TODO", "FIXME", "HACK"}\n'
                'if marker not in {"TODO", "FIXME", "HACK"}:\n'
                "    pass\n"
                "# TODO: real maintenance item\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(root), "add", "src/vocabulary.py"], check=True)
            report = discovery.discover(root)
            self.assertEqual(report["candidate_count"], 1)
            evidence = report["candidates"][0]["evidence"]
            self.assertEqual(evidence["path"], "src/vocabulary.py")
            self.assertEqual(evidence["line"], 4)
            self.assertEqual(evidence["marker"], "TODO")

    def test_ignores_test_files_and_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            fixture = root / "tests" / "test_sample.py"
            fixture.parent.mkdir()
            fixture.write_text(
                'source.write_text("# TODO: fixture marker\\n", encoding="utf-8")\n'
                "# FIXME: marker in a test comment\n",
                encoding="utf-8",
            )
            source = root / "src" / "sample.py"
            source.parent.mkdir()
            source.write_text("# TODO: real maintenance item\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", "tests/test_sample.py", "src/sample.py"],
                check=True,
            )
            report = discovery.discover(root)
            self.assertEqual(report["candidate_count"], 1)
            self.assertEqual(report["candidates"][0]["evidence"]["path"], "src/sample.py")
            self.assertEqual(report["skipped_files"], 1)

    def test_ignores_markers_inside_string_literals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            (root / "sample.py").write_text(
                'DEFAULT_DESCRIPTION = "TODO: describe this project"\n'
                'DOCSTRING = """\n'
                "TODO: inside a docstring\n"
                '"""\n'
                "# TODO: real maintenance item\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(root), "add", "sample.py"], check=True)
            report = discovery.discover(root)
            self.assertEqual(report["candidate_count"], 1)
            self.assertEqual(report["candidates"][0]["evidence"]["line"], 5)

    def test_reports_markers_after_unpaired_apostrophes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            (root / "notes.py").write_text("# don't drop this TODO later\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "notes.py"], check=True)
            report = discovery.discover(root)
            self.assertEqual(report["candidate_count"], 1)
            self.assertEqual(report["candidates"][0]["evidence"]["marker"], "TODO")

    def test_rejects_non_repository_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                discovery.discover(Path(tmp))


if __name__ == "__main__":
    unittest.main()
