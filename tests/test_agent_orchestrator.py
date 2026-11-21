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

    def test_approval_requires_review_state_and_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state = {"tasks": {"a": {"status": "pending"}}}
            with self.assertRaisesRegex(ValueError, "only awaiting_review"):
                orchestrator.approve("a", state, state_path)

    def test_approval_marks_handoff_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            handoff_path = Path(tmp) / "handoff.json"
            handoff_path.write_text(json.dumps({"status": "partial"}))
            state_path = Path(tmp) / "state.json"
            state = {"updated_at": None, "tasks": {"a": {
                "status": "awaiting_review", "handoff": str(handoff_path)}}}
            orchestrator.approve("a", state, state_path)
            self.assertEqual(state["tasks"]["a"]["status"], "completed")
            self.assertTrue(state_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
