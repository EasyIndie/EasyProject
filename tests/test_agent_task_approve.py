import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "agent-task-approve.py"
SPEC = importlib.util.spec_from_file_location("easyproject_agent_task_approve", MODULE_PATH)
approval = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(approval)


class AgentTaskApprovalTests(unittest.TestCase):
    def make_repo(self, root):
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        (root / ".ai/runtime/schemas").mkdir(parents=True)
        schema = (ROOT / ".ai/runtime/schemas/task.schema.json").read_text(encoding="utf-8")
        (root / ".ai/runtime/schemas/task.schema.json").write_text(schema, encoding="utf-8")
        source = root / "src" / "sample.py"
        source.parent.mkdir()
        source.write_text("# TODO: fix parser\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True)
        return source

    def make_report(self, root, source):
        relative = source.relative_to(root).as_posix()
        raw = source.read_bytes()
        candidate_id = "DISC-0123456789ab"
        return {
            "repository": root.name,
            "base_sha": subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
            ).strip(),
            "candidates": [{
                "candidate_id": candidate_id,
                "evidence": {
                    "path": relative, "line": 1, "marker": "TODO",
                    "file_sha256": __import__("hashlib").sha256(raw).hexdigest(),
                },
            }],
        }, candidate_id

    def promote(self, root, report, candidate_id, **kwargs):
        return approval.promote(
            root, report, candidate_id,
            objective="Resolve the parser TODO with a focused regression test.",
            acceptance_criteria=["The marker is resolved.", "A regression test covers the behavior."],
            approval_note="Reviewed and approved for this bounded change.",
            **kwargs,
        )

    def test_write_permission_requires_explicit_approval_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            source = self.make_repo(root)
            report, candidate_id = self.make_report(root, source)
            result = self.promote(root, report, candidate_id)
            self.assertFalse(result["task"]["permissions"]["repository_write"])
            self.assertEqual(result["approval_mode"], "read-only")
            self.assertFalse(result["execution"]["agent_invoked"])

    def test_explicit_write_approval_promotes_schema_valid_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            source = self.make_repo(root)
            report, candidate_id = self.make_report(root, source)
            result = self.promote(root, report, candidate_id, approve_write=True,
                                  checks=["python-unittest"])
            self.assertTrue(result["task"]["permissions"]["repository_write"])
            self.assertFalse(result["task"]["permissions"]["network_access"])
            self.assertFalse(result["task"]["permissions"]["secret_access"])
            self.assertFalse(result["task"]["permissions"]["external_side_effects"])
            self.assertEqual(result["approval_mode"], "write-enabled")
            self.assertFalse(result["execution"]["started"])

    def test_rejects_stale_source_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            source = self.make_repo(root)
            report, candidate_id = self.make_report(root, source)
            source.write_text("# TODO: changed after scan\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.promote(root, report, candidate_id, approve_write=True)

    def test_rejects_stale_base_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            source = self.make_repo(root)
            report, candidate_id = self.make_report(root, source)
            (root / "another.py").write_text("pass\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "another.py"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "advance"], check=True)
            with self.assertRaises(ValueError):
                self.promote(root, report, candidate_id)

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            source = self.make_repo(root)
            report, candidate_id = self.make_report(root, source)
            report["candidates"][0]["evidence"]["path"] = "../outside.py"
            with self.assertRaises(ValueError):
                self.promote(root, report, candidate_id)


if __name__ == "__main__":
    unittest.main()
