#!/usr/bin/env python3
"""Tests for the fail-closed sandbox launcher contract (not kernel enforcement)."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sandbox_runtime", ROOT / "scripts/sandbox_runtime.py")
sandbox = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(sandbox)


def profile() -> dict:
    return {
        "protocol_version": "1.0",
        "profile_id": "task-developer",
        "isolation_level": "workspace-write",
        "platform": "auto",
        "filesystem": {
            "workspace_read": True, "workspace_write": True,
            "stable_checkout": "deny", "other_agent_workspaces": "deny",
            "user_home": "deny", "credentials": "deny", "runtime_directory": "deny",
            "temporary_directory": "private", "read_only_paths": [], "write_paths": ["."]
        },
        "process": {
            "isolated_process_tree": True, "inherit_sandbox": True,
            "resource_limits": True, "timeout_enforced": True,
            "privilege_escalation": "deny", "max_cpu": 2,
            "max_memory_mb": 2048, "max_processes": 128, "timeout_seconds": 1800
        },
        "network": {
            "default": "deny", "allowed_domains": [],
            "allow_lan": False, "allow_host": False, "egress_proxy_required": True
        },
        "secrets": {
            "inherit_host_environment": False, "credential_mounts": False,
            "brokered_credentials": []
        },
        "artifacts": {
            "export": ["diff"], "direct_workspace_sharing": False,
            "symlink_policy": "reject-escape"
        }
    }


class FakeBackend:
    backend_id = "test-backend"

    def probe(self):
        return sandbox.SandboxCapabilities(
            self.backend_id, sandbox.host_platform(), True, True, True, True,
            True, False, "ready", "test double only"
        )

    def build_command(self, command, spec):
        return ["sandbox-test-wrapper", *command]


class SandboxRuntimeTests(unittest.TestCase):
    def test_doctor_fails_closed_when_no_backend_is_registered(self):
        doctor = sandbox.SandboxManager().doctor()
        self.assertFalse(doctor["enforcement_ready"])
        self.assertEqual(doctor["fallback"], "forbidden")
        self.assertEqual(doctor["backends"][0]["status"], "not-implemented")

    def test_valid_profile_has_stable_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(json.dumps(profile()), encoding="utf-8")
            _, first = sandbox.load_profile(path)
            _, second = sandbox.load_profile(path)
            self.assertEqual(first, second)
            self.assertEqual(len(first), 64)

    def test_invalid_profile_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            value = profile()
            value["network"]["allow_lan"] = True
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(sandbox.SandboxProfileError):
                sandbox.load_profile(path)

    def test_missing_backend_refuses_to_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profile.json"
            profile_path.write_text(json.dumps(profile()), encoding="utf-8")
            with self.assertRaises(sandbox.SandboxBackendUnavailable):
                sandbox.SandboxManager().build_command(
                    ["pi"], profile_path, "task-1", Path(tmp), Path(tmp) / "runtime"
                )

    def test_registered_backend_receives_frozen_policy_and_wraps_whole_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profile.json"
            profile_path.write_text(json.dumps(profile()), encoding="utf-8")
            manager = sandbox.SandboxManager([FakeBackend()])
            command, evidence = manager.build_command(
                ["claude", "-p"], profile_path, "task-1",
                Path(tmp), Path(tmp) / "runtime"
            )
            self.assertEqual(command, ["sandbox-test-wrapper", "claude", "-p"])
            self.assertEqual(evidence["status"], "enforced")
            self.assertEqual(evidence["backend"], "test-backend")
            self.assertEqual(len(evidence["profile_sha256"]), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
