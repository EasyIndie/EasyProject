import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "agent-discover.py"
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
            first = report["candidates"][0]
            self.assertEqual(first["evidence"]["path"], "src/sample.py")
            self.assertIn(first["evidence"]["marker"], {"TODO", "FIXME"})
            self.assertFalse(first["task"]["permissions"]["repository_write"])
            self.assertFalse(first["task"]["permissions"]["network_access"])
            self.assertEqual(first["task"]["risk"], "low")

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

    def test_rejects_non_repository_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                discovery.discover(Path(tmp))


if __name__ == "__main__":
    unittest.main()
