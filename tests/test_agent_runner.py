#!/usr/bin/env python3
"""Unit tests for harness command construction and permission boundaries."""
from __future__ import annotations

import importlib.util
import json
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

    def test_pi_rejects_write_permission(self) -> None:
        with self.assertRaises(ValueError):
            agent_run.build_command("pi", task(write=True), "prompt")

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
