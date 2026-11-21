#!/usr/bin/env python3
"""Unit tests for harness command construction and permission boundaries."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("agent_run", ROOT / "scripts/agent-run.py")
agent_run = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(agent_run)


def task(write: bool = False) -> dict:
    return {"permissions": {
        "repository_read": True, "repository_write": write,
        "network_access": False, "secret_access": False,
        "external_side_effects": False,
    }}


class AgentRunnerTests(unittest.TestCase):

    def test_run_harness_enforces_timeout_and_stops_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, stdout, stderr, reason = agent_run.run_harness(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                Path(tmp), 0.1,
            )
            self.assertEqual(code, 124)
            self.assertEqual(reason, "timeout")

    def test_run_harness_observes_cancellation_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            cancel_file = Path(tmp) / "cancel.request"
            cancel_file.write_text("requested", encoding="utf-8")
            code, stdout, stderr, reason = agent_run.run_harness(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                Path(tmp), 5, cancel_file,
            )
            self.assertEqual(code, 130)
            self.assertEqual(reason, "cancelled")

    def test_workspace_path_is_resolved_and_must_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = agent_run.resolve_workspace(Path(tmp))
            self.assertEqual(workspace, Path(tmp).resolve())
            with self.assertRaisesRegex(ValueError, "does not exist"):
                agent_run.resolve_workspace(Path(tmp) / "missing")

    def test_codex_uses_workspace_scoped_sandbox(self) -> None:
        command = agent_run.build_command("codex", task(write=True), "prompt")
        self.assertIn("workspace-write", command)
        self.assertIn("--ask-for-approval", command)
        self.assertIn("on-request", command)

    def test_codex_read_only_uses_read_only_sandbox(self) -> None:
        self.assertIn("read-only", agent_run.build_command("codex", task(), "prompt"))

    def test_claude_read_only_uses_plan_mode(self) -> None:
        command = agent_run.build_command("claude-code", task(), "prompt")
        self.assertIn("--permission-mode", command)
        self.assertIn("plan", command)

    def test_pi_write_requires_explicit_unsandboxed_acknowledgement(self) -> None:
        with self.assertRaisesRegex(ValueError, "pi_unsandboxed_write"):
            agent_run.build_command("pi", task(write=True), "prompt")

    def test_pi_write_requires_explicit_runtime_flag(self) -> None:
        with self.assertRaisesRegex(ValueError, "allow-unsandboxed-pi-write"):
            agent_run.build_command("pi", task(write=True), "prompt")

    def test_pi_explicit_unsafe_write_exposes_edit_and_shell_tools(self) -> None:
        request = task(write=True)
        command = agent_run.build_command(
            "pi", request, "prompt", allow_unsandboxed_pi_write=True
        )
        tools = command[command.index("--tools") + 1]
        self.assertEqual(
            set(tools.split(",")),
            {"read", "grep", "find", "ls", "edit", "write", "bash"},
        )

    def test_pi_read_only_exposes_only_read_tools(self) -> None:
        command = agent_run.build_command("pi", task(), "prompt")
        tools = command[command.index("--tools") + 1]
        self.assertEqual(set(tools.split(",")), {"read", "grep", "find", "ls"})

    def test_network_secret_and_external_effects_fail_closed(self) -> None:
        for permission in ("network_access", "secret_access", "external_side_effects"):
            request = task()
            request["permissions"][permission] = True
            with self.subTest(permission=permission), self.assertRaises(ValueError):
                agent_run.build_command("codex", request, "prompt")

    def test_example_task_validates_against_schema(self) -> None:
        from jsonschema import Draft202012Validator
        schema = json.loads((ROOT / ".ai/runtime/schemas/task.schema.json").read_text())
        example = json.loads((ROOT / ".ai/runtime/examples/task.json").read_text())
        Draft202012Validator(schema).validate(example)

    def test_handoff_artifact_fields_validate(self) -> None:
        from jsonschema import Draft202012Validator
        schema = json.loads((ROOT / ".ai/runtime/schemas/handoff.schema.json").read_text())
        handoff = json.loads((ROOT / ".ai/runtime/examples/handoff.json").read_text())
        handoff["artifacts"] = {"stdout_path": "run.stdout.txt", "stderr_path": "run.stderr.txt", "exit_code": 0}
        Draft202012Validator(schema).validate(handoff)


if __name__ == "__main__":
    unittest.main(verbosity=2)
