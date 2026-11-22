#!/usr/bin/env python3
"""Tests for DAG validation and approval-gated orchestration."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
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

    def test_acceptance_check_command_can_be_cancelled(self):
        with tempfile.TemporaryDirectory() as tmp:
            cancel_file = Path(tmp) / "cancel.request"
            cancel_file.write_text("requested", encoding="utf-8")
            code, stdout, stderr, reason = orchestrator.run_command_controlled(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                Path(tmp), 5, cancel_file,
            )
            self.assertEqual(code, 130)
            self.assertEqual(reason, "cancelled")

    def test_cancelled_dependency_blocks_downstream_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            state = orchestrator.initial_state(plan([item("a"), item("b", ["a"])]), use_worktrees=True)
            state["tasks"]["a"]["status"] = "cancelled"
            result = orchestrator.run_plan(plan([item("a"), item("b", ["a"])]), runs, state, True)
            self.assertEqual(result, 0)
            self.assertEqual(state["tasks"]["b"]["status"], "blocked")
            self.assertTrue((runs / "orchestrator-state.json").is_file())

    def test_cancel_request_only_targets_the_active_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            state = {"tasks": {"task-a": {"status": "running", "attempts": 2}}}
            marker = orchestrator.request_cancel("task-a", state, runs)
            payload = json.loads(marker.read_text(encoding="utf-8"))
            self.assertEqual(payload["task_id"], "task-a")
            self.assertEqual(payload["attempt"], 2)
            self.assertTrue(marker.name.endswith("cancel-attempt-2.request"))
            state["tasks"]["task-a"]["status"] = "awaiting_review"
            with self.assertRaisesRegex(ValueError, "only running tasks"):
                orchestrator.request_cancel("task-a", state, runs)

    def test_pi_write_authorization_comes_only_from_control_plane_flag(self):
        task_path = Path("task.json")
        output = Path("handoff.json")
        workspace = Path("workspace")
        cancel = Path("cancel.request")
        # An editable Task Envelope is not an authorization source.
        command = orchestrator.build_runner_command(
            task_path, "pi", output, workspace, cancel, False
        )
        self.assertNotIn("--allow-unsandboxed-pi-write", command)
        # Only the explicit trusted control-plane flag grants the override.
        command = orchestrator.build_runner_command(
            task_path, "pi", output, workspace, cancel, True
        )
        self.assertIn("--allow-unsandboxed-pi-write", command)

    def test_sandbox_requirement_is_passed_from_control_plane_not_task_envelope(self):
        command = orchestrator.build_runner_command(
            Path("task.json"), "claude-code", Path("handoff.json"),
            Path("workspace"), Path("cancel.request"), False,
            require_sandbox=True, sandbox_profile=Path("/trusted/profile.json"),
        )
        self.assertIn("--require-sandbox", command)
        self.assertIn("--sandbox-profile", command)
        self.assertIn("/trusted/profile.json", command)
        state = orchestrator.initial_state(
            plan([item("task-a")]), sandbox_required=True,
            sandbox_profile="/trusted/profile.json",
            sandbox_profile_sha256="a" * 64,
        )
        self.assertTrue(state["sandbox_required"])
        self.assertEqual(state["sandbox_profile_sha256"], "a" * 64)

    def test_sandboxed_acceptance_checks_fail_closed_without_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            with self.assertRaisesRegex(RuntimeError, "No registered backend"):
                orchestrator.run_acceptance_checks(
                    ["python-unittest"], workspace, root / "runs",
                    "task-a", 1, require_sandbox=True,
                    sandbox_profile=ROOT / ".ai/runtime/examples/sandbox-profile.json",
                    task_permissions={
                        "repository_read": True, "repository_write": True,
                        "network_access": False, "secret_access": False,
                    },
                )

    def test_review_artifact_is_portable_and_bound_to_review_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "runs"
            task_dir = runs / "task-a"
            task_dir.mkdir(parents=True)
            diff_path = task_dir / "review.diff"
            diff_path.write_text("diff --git a/a.txt b/a.txt\\n", encoding="utf-8")
            evidence = {
                "protocol_version": "1.0",
                "task_id": "task-a",
                "base_commit": "abcdef0123456789",
                "captured_at": "2026-11-22T00:00:00+00:00",
                "changed_files": ["a.txt"],
                "diff_stat": "1 file changed",
                "diff_check": {"result": "passed", "output": ""},
                "fingerprint": "a" * 64,
                "diff_path": str(diff_path),
                "acceptance": {"automated_checks": {"status": "passed", "results": [{
                    "stdout_path": str(task_dir / "checks" / "stdout.txt"),
                    "stderr_path": str(task_dir / "checks" / "stderr.txt"),
                }]}},
            }
            evidence_path = task_dir / "review-evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            artifact = orchestrator.publish_review_artifact(
                evidence, runs, "task-a", 1,
                {
                    "sandbox_status": "enforced",
                    "sandbox_backend": "test-backend",
                    "sandbox_profile_sha256": "b" * 64,
                },
            )
            record = {
                "task_id": "task-a",
                "review_evidence": str(evidence_path),
                "review_artifact": artifact,
            }
            manifest = orchestrator.verify_review_artifact(record)
            self.assertEqual(manifest["kind"], "review-evidence")
            portable = json.loads(
                (Path(artifact["artifact_dir"]) / "review-evidence.json").read_text(encoding="utf-8")
            )
            self.assertEqual(portable["diff_path"], "review.diff")
            self.assertEqual(portable["acceptance"]["automated_checks"]["results"][0]["stdout_path"], "stdout.txt")

    def test_sandbox_required_approval_rejects_missing_immutable_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "handoff.json"
            handoff.write_text(json.dumps({"task_id": "task-a", "status": "partial"}), encoding="utf-8")
            state = orchestrator.initial_state(plan([item("task-a")]), sandbox_required=True)
            record = state["tasks"]["task-a"]
            record.update(status="awaiting_review", handoff=str(handoff),
                          automated_checks={"status": "passed", "results": []})
            with self.assertRaisesRegex(ValueError, "immutable review artifact"):
                orchestrator.approve("task-a", state, root / "state.json")

    def test_valid_dag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(plan([item("a"), item("b", ["a"])])))
            loaded = orchestrator.load_plan(path)
            self.assertEqual([task["task_id"] for task in loaded["tasks"]], ["a", "b"])

    def test_task_file_may_live_in_configured_external_runs_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "external" / "runs"
            runs.mkdir(parents=True)
            task = runs / "task.json"
            task.write_text("{}", encoding="utf-8")
            resolved = orchestrator.resolve_task_path(str(task), runs)
            self.assertEqual(resolved, task.resolve())

    def test_task_file_outside_repository_and_runs_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "runs"
            outside = root / "untrusted" / "task.json"
            runs.mkdir()
            outside.parent.mkdir()
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "configured runs directory"):
                orchestrator.resolve_task_path(str(outside), runs)

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
            dependent_record = {"worktree": None, "base_commit": None}
            dependent = orchestrator.prepare_worktree(
                root, Path(tmp) / "dependent-runs", "dependent", dependent_record
            )
            self.assertEqual(dependent_record["base_commit"], orchestrator.git_output(root, "rev-parse", "HEAD"))
            self.assertEqual((dependent / "file.txt").read_text(encoding="utf-8"), "agent change\\n")

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
