#!/usr/bin/env python3
"""Tests for DAG validation and approval-gated orchestration."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("agent_orchestrate", ROOT / "scripts/agent-orchestrate.py")
orchestrator = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(orchestrator)


def plan(tasks):
    return {"protocol_version": "1.0", "tasks": tasks}


def item(task_id, deps=None):
    return {"task_id": task_id, "task_file": ".ai/runtime/examples/task.json",
            "harness": "codex", "depends_on": deps or [], "max_attempts": 2}


class OrchestratorTests(unittest.TestCase):
    def test_allowlisted_acceptance_check_runs_and_persists_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            (workspace / "tests").mkdir(parents=True)
            (workspace / "tests" / "test_sample.py").write_text(
                "import unittest\nclass SampleTests(unittest.TestCase):\n"
                "    def test_ok(self): self.assertTrue(True)\n",
                encoding="utf-8",
            )
            result = orchestrator.run_acceptance_checks(
                ["python-unittest"], workspace, Path(tmp) / "runs", "task-a", 1
            )
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["results"][0]["result"], "passed")
            self.assertTrue(Path(result["results"][0]["stdout_path"]).is_file())
            self.assertTrue(Path(result["results"][0]["stderr_path"]).is_file())

    def test_failed_acceptance_check_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            (workspace / "tests").mkdir(parents=True)
            (workspace / "tests" / "test_failure.py").write_text(
                "import unittest\nclass FailureTests(unittest.TestCase):\n"
                "    def test_fail(self): self.fail('expected failure')\n",
                encoding="utf-8",
            )
            result = orchestrator.run_acceptance_checks(
                ["python-unittest"], workspace, Path(tmp) / "runs", "task-a", 1
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["results"][0]["result"], "failed")
            self.assertNotEqual(result["results"][0]["exit_code"], 0)

    def test_unknown_acceptance_check_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Unsupported acceptance check"):
            orchestrator.acceptance_command("arbitrary-shell")

    def test_valid_dag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(plan([item("a"), item("b", ["a"])])))
            loaded = orchestrator.load_plan(path)
            self.assertEqual([task["task_id"] for task in loaded["tasks"]], ["a", "b"])

    def test_unknown_dependency_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(plan([item("a", ["missing"])])))
            with self.assertRaisesRegex(ValueError, "unknown dependency"):
                orchestrator.load_plan(path)

    def test_cycle_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(plan([item("a", ["b"]), item("b", ["a"])])))
            with self.assertRaisesRegex(ValueError, "cycle"):
                orchestrator.load_plan(path)

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(plan([item("a"), item("a")])))
            with self.assertRaisesRegex(ValueError, "duplicate"):
                orchestrator.load_plan(path)


    def test_dry_run_lists_full_dag_without_creating_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "plan.json"
            runs_dir = root / "runs"
            plan_path.write_text(json.dumps(plan([item("a"), item("b", ["a"])])))
            output = io.StringIO()
            with patch("sys.argv", ["agent-orchestrate", "--plan", str(plan_path),
                                    "--runs-dir", str(runs_dir), "--dry-run"]):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(orchestrator.main(), 0)
            self.assertIn("READY a:", output.getvalue())
            self.assertIn("READY b:", output.getvalue())
            self.assertFalse((runs_dir / "orchestrator-state.json").exists())


    def test_task_ids_are_safe_path_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(plan([item("../escape")])))
            with self.assertRaisesRegex(ValueError, "Invalid or duplicate"):
                orchestrator.load_plan(path)

    def test_worktree_is_created_and_reused_for_same_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
            (root / "README.md").write_text("fixture\\n")
            subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
            record = {"worktree": None, "base_commit": None}
            runs = Path(tmp) / "runs"
            worktree = orchestrator.prepare_worktree(root, runs, "task-one", record)
            self.assertTrue((worktree / "README.md").is_file())
            self.assertFalse(worktree.is_relative_to(root))
            self.assertEqual(orchestrator.prepare_worktree(root, runs, "task-one", record), worktree)
            top = subprocess.run(["git", "-C", str(worktree), "rev-parse", "--show-toplevel"],
                                 check=True, capture_output=True, text=True).stdout.strip()
            self.assertEqual(top, str(worktree))

    def test_worktree_rejects_missing_recorded_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            record = {"worktree": str(Path(tmp) / "missing"), "base_commit": "deadbeef"}
            with self.assertRaisesRegex(ValueError, "recorded worktree is missing"):
                orchestrator.prepare_worktree(root, Path(tmp) / "runs", "task-one", record)

    def test_change_evidence_includes_tracked_and_untracked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
            (root / "tracked.txt").write_text("before\\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
            base = orchestrator.git_output(root, "rev-parse", "HEAD")
            (root / "tracked.txt").write_text("after\\n", encoding="utf-8")
            (root / "new.txt").write_text("new file\\n", encoding="utf-8")
            evidence = orchestrator.collect_change_evidence(root, base, "task-a", Path(tmp) / "runs")
            self.assertEqual(evidence["changed_files"], ["new.txt", "tracked.txt"])
            self.assertTrue(Path(evidence["diff_path"]).is_file())
            self.assertEqual(evidence["acceptance"]["status"], "pending_human_review")
            self.assertEqual(evidence["diff_check"]["result"], "passed")

    def test_approval_rejects_workspace_changed_after_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
            (root / "file.txt").write_text("before\\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "file.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
            base = orchestrator.git_output(root, "rev-parse", "HEAD")
            (root / "file.txt").write_text("reviewed\\n", encoding="utf-8")
            runs = Path(tmp) / "runs"
            evidence = orchestrator.collect_change_evidence(root, base, "a", runs)
            record = {"review_evidence": evidence["evidence_path"]}
            (root / "file.txt").write_text("changed after review\\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after review"):
                orchestrator.verify_change_evidence(root, record)
            saved = json.loads(Path(evidence["evidence_path"]).read_text(encoding="utf-8"))
            self.assertEqual(saved["fingerprint"], evidence["fingerprint"])

    def _integration_fixture(self, tmp):
        root = Path(tmp) / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
        (root / "file.txt").write_text("base\\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "file.txt"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
        runs = Path(tmp) / "runs"
        record = {"worktree": None, "base_commit": None}
        worktree = orchestrator.prepare_worktree(root, runs, "a", record)
        (worktree / "file.txt").write_text("agent change\\n", encoding="utf-8")
        (worktree / "new.txt").write_text("new file\\n", encoding="utf-8")
        evidence = orchestrator.collect_change_evidence(worktree, record["base_commit"], "a", runs)
        record.update(
            status="awaiting_review",
            handoff=str(Path(tmp) / "handoff.json"),
            review_evidence=evidence["evidence_path"],
        )
        Path(record["handoff"]).write_text(json.dumps({"task_id": "a", "status": "partial"}))
        state = {"updated_at": None, "tasks": {"a": record}}
        state_path = Path(tmp) / "state.json"
        orchestrator.approve("a", state, state_path)
        self.assertEqual(record["status"], "approved")
        return root, worktree, state, state_path

    def test_approved_worktree_is_committed_and_cherry_picked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, worktree, state, state_path = self._integration_fixture(tmp)
            orchestrator.integrate_task(root, "a", state, state_path)
            record = state["tasks"]["a"]
            self.assertEqual(record["status"], "completed")
            self.assertEqual(record["integration_state"], "completed")
            self.assertEqual((root / "file.txt").read_text(encoding="utf-8"), "agent change\\n")
            self.assertEqual((root / "new.txt").read_text(encoding="utf-8"), "new file\\n")
            self.assertEqual(orchestrator.git_output(root, "status", "--porcelain=v1"), "")
            self.assertNotEqual(record["integration_commit"], record["base_commit"])

    def test_integration_includes_agent_commits_and_later_untracked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
            (root / "file.txt").write_text("base\\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "file.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
            runs = Path(tmp) / "runs"
            record = {"worktree": None, "base_commit": None}
            worktree = orchestrator.prepare_worktree(root, runs, "a", record)
            (worktree / "file.txt").write_text("agent committed\\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(worktree), "add", "file.txt"], check=True)
            subprocess.run(["git", "-C", str(worktree), "commit", "-qm", "agent change"], check=True)
            (worktree / "later.txt").write_text("untracked after commit\\n", encoding="utf-8")
            evidence = orchestrator.collect_change_evidence(worktree, record["base_commit"], "a", runs)
            self.assertEqual(evidence["changed_files"], ["file.txt", "later.txt"])
            record.update(
                status="awaiting_review",
                handoff=str(Path(tmp) / "handoff.json"),
                review_evidence=evidence["evidence_path"],
            )
            Path(record["handoff"]).write_text(json.dumps({"task_id": "a", "status": "partial"}))
            state = {"updated_at": None, "tasks": {"a": record}}
            state_path = Path(tmp) / "state.json"
            orchestrator.approve("a", state, state_path)
            orchestrator.integrate_task(root, "a", state, state_path)
            self.assertEqual(record["status"], "completed")
            self.assertEqual((root / "file.txt").read_text(encoding="utf-8"), "agent committed\\n")
            self.assertEqual((root / "later.txt").read_text(encoding="utf-8"), "untracked after commit\\n")

    def test_integration_conflict_is_preserved_and_can_be_finalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, worktree, state, state_path = self._integration_fixture(tmp)
            (root / "file.txt").write_text("target change\\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "file.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "target change"], check=True)
            with self.assertRaisesRegex(ValueError, "conflict"):
                orchestrator.integrate_task(root, "a", state, state_path)
            record = state["tasks"]["a"]
            self.assertEqual(record["status"], "integration_conflict")
            self.assertEqual(
                orchestrator.git_result(root, "rev-parse", "--verify", "CHERRY_PICK_HEAD").returncode,
                0,
            )
            (root / "file.txt").write_text("manually resolved\\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "file.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "-c", "core.editor=true", "cherry-pick", "--continue"],
                check=True,
            )
            orchestrator.integrate_task(root, "a", state, state_path)
            self.assertEqual(record["status"], "completed")
            self.assertEqual(record["integration_state"], "completed")
            self.assertEqual((root / "file.txt").read_text(encoding="utf-8"), "manually resolved\\n")

    def test_approval_requires_review_state_and_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state = {"tasks": {"a": {"status": "pending"}}}
            with self.assertRaisesRegex(ValueError, "only awaiting_review"):
                orchestrator.approve("a", state, state_path)

    def test_failed_automated_checks_block_human_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            handoff_path = Path(tmp) / "handoff.json"
            handoff_path.write_text(json.dumps({"task_id": "a", "status": "partial"}))
            state_path = Path(tmp) / "state.json"
            state = {"updated_at": None, "tasks": {"a": {
                "status": "awaiting_review",
                "handoff": str(handoff_path),
                "automated_checks": {"status": "failed", "results": []},
            }}}
            with self.assertRaisesRegex(ValueError, "acceptance checks failed"):
                orchestrator.approve("a", state, state_path)
            self.assertEqual(state["tasks"]["a"]["status"], "awaiting_review")

    def test_approval_marks_handoff_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            handoff_path = Path(tmp) / "handoff.json"
            handoff_path.write_text(json.dumps({"task_id": "a", "status": "partial"}))
            state_path = Path(tmp) / "state.json"
            state = {"updated_at": None, "tasks": {"a": {
                "status": "awaiting_review", "handoff": str(handoff_path)}}}
            orchestrator.approve("a", state, state_path)
            self.assertEqual(state["tasks"]["a"]["status"], "completed")
            self.assertTrue(state_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
