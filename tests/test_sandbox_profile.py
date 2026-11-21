#!/usr/bin/env python3
"""Contract tests for declarative sandbox profiles (not OS enforcement tests)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / ".ai/runtime/schemas/sandbox-profile.schema.json").read_text())


def baseline_profile() -> dict:
    return {
        "protocol_version": "1.0",
        "profile_id": "task-developer",
        "isolation_level": "workspace-write",
        "platform": "auto",
        "filesystem": {
            "workspace_read": True,
            "workspace_write": True,
            "stable_checkout": "deny",
            "other_agent_workspaces": "deny",
            "user_home": "deny",
            "credentials": "deny",
            "runtime_directory": "deny",
            "temporary_directory": "private",
            "read_only_paths": [],
            "write_paths": ["."],
        },
        "process": {
            "isolated_process_tree": True,
            "inherit_sandbox": True,
            "resource_limits": True,
            "timeout_enforced": True,
            "privilege_escalation": "deny",
            "max_cpu": 2,
            "max_memory_mb": 2048,
            "max_processes": 128,
            "timeout_seconds": 1800,
        },
        "network": {
            "default": "deny",
            "allowed_domains": [],
            "allow_lan": False,
            "allow_host": False,
            "egress_proxy_required": True,
        },
        "secrets": {
            "inherit_host_environment": False,
            "credential_mounts": False,
            "brokered_credentials": [],
        },
        "artifacts": {
            "export": ["diff", "handoff", "test-report"],
            "direct_workspace_sharing": False,
            "symlink_policy": "reject-escape",
        },
    }


class SandboxProfileTests(unittest.TestCase):
    def test_baseline_workspace_write_profile_validates(self):
        Draft202012Validator(SCHEMA).validate(baseline_profile())

    def test_read_only_profile_cannot_enable_workspace_write(self):
        profile = baseline_profile()
        profile["isolation_level"] = "read-only"
        profile["filesystem"]["workspace_write"] = False
        Draft202012Validator(SCHEMA).validate(profile)
        profile["filesystem"]["workspace_write"] = True
        with self.assertRaises(Exception):
            Draft202012Validator(SCHEMA).validate(profile)

    def test_profile_cannot_allow_stable_checkout_or_other_agents(self):
        for key in ("stable_checkout", "other_agent_workspaces"):
            profile = baseline_profile()
            profile["filesystem"][key] = "allow"
            with self.subTest(key=key), self.assertRaises(Exception):
                Draft202012Validator(SCHEMA).validate(profile)

    def test_profile_cannot_inherit_host_secrets_or_environment(self):
        profile = baseline_profile()
        profile["secrets"]["inherit_host_environment"] = True
        with self.assertRaises(Exception):
            Draft202012Validator(SCHEMA).validate(profile)
        profile = baseline_profile()
        profile["secrets"]["credential_mounts"] = True
        with self.assertRaises(Exception):
            Draft202012Validator(SCHEMA).validate(profile)

    def test_profile_cannot_enable_lan_or_host_network(self):
        for key in ("allow_lan", "allow_host"):
            profile = baseline_profile()
            profile["network"][key] = True
            with self.subTest(key=key), self.assertRaises(Exception):
                Draft202012Validator(SCHEMA).validate(profile)

    def test_profile_requires_artifact_broker_semantics(self):
        profile = baseline_profile()
        profile["artifacts"]["direct_workspace_sharing"] = True
        with self.assertRaises(Exception):
            Draft202012Validator(SCHEMA).validate(profile)

    def test_unknown_policy_fields_are_rejected(self):
        profile = baseline_profile()
        profile["disable_sandbox"] = True
        with self.assertRaises(Exception):
            Draft202012Validator(SCHEMA).validate(profile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
