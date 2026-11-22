#!/usr/bin/env python3
"""Fail-closed task sandbox contract and backend registry.

This module deliberately ships no permissive fallback backend. A task is only
sandboxed when a registered backend reports effective enforcement and launches
the complete harness process tree inside that boundary.
"""
from __future__ import annotations

import copy
import hashlib
import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROFILE_SCHEMA = ROOT / ".ai/runtime/schemas/sandbox-profile.schema.json"


class SandboxError(RuntimeError):
    """Base error for sandbox policy and launch failures."""


class SandboxProfileError(SandboxError):
    """The requested profile is invalid or cannot be safely interpreted."""


class SandboxBackendUnavailable(SandboxError):
    """No backend can enforce the complete requested profile."""


class SandboxEnforcementError(SandboxError):
    """A backend failed to establish the requested boundary."""


@dataclass(frozen=True)
class SandboxCapabilities:
    backend_id: str
    platform: str
    available: bool
    enforces_filesystem: bool
    enforces_network: bool
    isolates_process_tree: bool
    enforces_resource_limits: bool
    supports_egress_proxy: bool
    supports_secrets_broker: bool
    status: str
    reason: str


@dataclass(frozen=True)
class SandboxLaunchSpec:
    task_id: str
    profile: dict
    profile_sha256: str
    workspace: Path
    runtime_directory: Path
    timeout_seconds: int


class SandboxBackend(Protocol):
    """Backend contract: wrap the whole Agent executable, not only its shell."""

    backend_id: str

    def probe(self) -> SandboxCapabilities:
        """Return verified host capability; do not infer enforcement from config."""

    def build_command(
        self, command: Sequence[str], spec: SandboxLaunchSpec
    ) -> list[str]:
        """Return a launcher argv that enforces every requested profile property."""

    def build_environment(self, spec: SandboxLaunchSpec) -> dict[str, str]:
        """Return a minimal launcher environment with no inherited host secrets."""


def load_profile(path: Path) -> tuple[dict, str]:
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SandboxProfileError(f"Cannot read sandbox profile: {exc}") from exc
    try:
        from jsonschema import Draft202012Validator
        schema = json.loads(PROFILE_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(profile)
    except ImportError as exc:
        raise SandboxProfileError(
            "Install jsonschema before validating or launching a sandbox profile."
        ) from exc
    except Exception as exc:
        raise SandboxProfileError(f"Sandbox profile validation failed: {exc}") from exc
    canonical = json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()
    return profile, hashlib.sha256(canonical).hexdigest()


def host_platform() -> str:
    value = platform.system().lower()
    return {"darwin": "macos", "linux": "linux", "windows": "windows"}.get(value, value)


class SandboxManager:
    """Selects only backends that explicitly prove complete policy support."""

    def __init__(self, backends: Sequence[SandboxBackend] = ()) -> None:
        self._backends = {backend.backend_id: backend for backend in backends}

    def capabilities(self) -> list[SandboxCapabilities]:
        if not self._backends:
            current = host_platform()
            planned = {
                "macos": "macos-seatbelt",
                "linux": "linux-rootless-oci",
                "windows": "windows-appcontainer",
            }.get(current, "no-backend")
            return [SandboxCapabilities(
                backend_id=planned,
                platform=current,
                available=False,
                enforces_filesystem=False,
                enforces_network=False,
                isolates_process_tree=False,
                enforces_resource_limits=False,
                supports_egress_proxy=False,
                supports_secrets_broker=False,
                status="not-implemented",
                reason="No production backend is registered; unsandboxed fallback is forbidden.",
            )]
        return [backend.probe() for backend in self._backends.values()]

    def doctor(self) -> dict:
        capabilities = self.capabilities()
        current = host_platform()
        ready = any(
            item.platform == current and item.available and item.enforces_filesystem
            and item.enforces_network and item.isolates_process_tree
            and item.enforces_resource_limits
            for item in capabilities
        )
        return {
            "protocol_version": "1.0",
            "host_platform": host_platform(),
            "enforcement_ready": ready,
            "fallback": "forbidden",
            "backends": [asdict(item) for item in capabilities],
        }

    def build_command(
        self,
        command: Sequence[str],
        profile_path: Path,
        task_id: str,
        workspace: Path,
        runtime_directory: Path,
        task_permissions: dict,
    ) -> tuple[list[str], dict[str, str], dict]:
        profile, _base_digest = load_profile(profile_path)
        filesystem = profile["filesystem"]
        if task_permissions.get("repository_write", False) and not task_permissions.get("repository_read", False):
            raise SandboxProfileError("Task write permission requires repository_read permission.")
        if task_permissions.get("repository_read", False) and not filesystem["workspace_read"]:
            raise SandboxProfileError("Task requests repository read, but the trusted profile denies workspace reads.")
        if task_permissions.get("repository_write", False) and not filesystem["workspace_write"]:
            raise SandboxProfileError("Task requests repository write, but the trusted profile denies workspace writes.")
        # Task permissions can only narrow the trusted maximum profile, never expand it.
        effective_profile = copy.deepcopy(profile)
        effective_profile["filesystem"]["workspace_read"] = bool(
            filesystem["workspace_read"] and task_permissions.get("repository_read", False)
        )
        effective_profile["filesystem"]["workspace_write"] = bool(
            filesystem["workspace_write"] and task_permissions.get("repository_write", False)
        )
        if not effective_profile["filesystem"]["workspace_write"]:
            effective_profile["filesystem"]["write_paths"] = []
        if not effective_profile["filesystem"]["workspace_read"]:
            effective_profile["filesystem"]["read_only_paths"] = []
        if not task_permissions.get("network_access", False):
            effective_profile["network"]["allowed_domains"] = []
        if not task_permissions.get("secret_access", False):
            effective_profile["secrets"]["brokered_credentials"] = []
        canonical = json.dumps(effective_profile, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(canonical).hexdigest()
        profile = effective_profile
        requested_platform = profile.get("platform", "auto")
        current = host_platform()
        if requested_platform not in ("auto", current):
            raise SandboxBackendUnavailable(
                f"Profile targets {requested_platform}, but current host is {current}."
            )
        timeout_seconds = int(profile["process"].get("timeout_seconds", 1800))
        spec = SandboxLaunchSpec(
            task_id=task_id,
            profile=profile,
            profile_sha256=digest,
            workspace=workspace.resolve(),
            runtime_directory=runtime_directory.resolve(),
            timeout_seconds=timeout_seconds,
        )
        requested_backend = profile.get("runtime", {}).get("backend")
        backend_aliases = {
            "macos-seatbelt": "macos-seatbelt",
            "linux-rootless-oci": "linux-rootless-oci",
            "rootless-docker": "rootless-docker",
            "windows-appcontainer": "windows-appcontainer",
            "wsl2-worker": "wsl2-worker",
            "gvisor": "gvisor", "kata": "kata", "firecracker": "firecracker",
        }
        selected_id = backend_aliases.get(requested_backend, requested_backend)
        candidates = []
        for backend in self._backends.values():
            if selected_id and backend.backend_id != selected_id:
                continue
            caps = backend.probe()
            needs_egress_proxy = bool(profile["network"].get("allowed_domains")) and profile["network"].get("egress_proxy_required", True)
            needs_secrets_broker = bool(profile["secrets"].get("brokered_credentials"))
            if (caps.platform == current and caps.available
                    and caps.enforces_filesystem and caps.enforces_network
                    and caps.isolates_process_tree and caps.enforces_resource_limits
                    and (not needs_egress_proxy or caps.supports_egress_proxy)
                    and (not needs_secrets_broker or caps.supports_secrets_broker)):
                candidates.append(backend)
        if not candidates:
            raise SandboxBackendUnavailable(
                "No registered backend can enforce filesystem, network, process-tree, "
                "and resource policies. Refusing to start the Agent unsandboxed."
            )
        backend = candidates[0]
        try:
            wrapped = backend.build_command(command, spec)
            environment = backend.build_environment(spec)
        except Exception as exc:
            raise SandboxEnforcementError(
                f"Backend {backend.backend_id} failed to construct an enforced launch: {exc}"
            ) from exc
        if not wrapped:
            raise SandboxEnforcementError("Backend returned an empty launcher command.")
        if not isinstance(environment, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                     for k, v in environment.items()):
            raise SandboxEnforcementError("Backend returned an invalid or inherited launcher environment.")
        evidence = {
            "status": "enforced",
            "backend": backend.backend_id,
            "profile_sha256": digest,
            "platform": current,
            "timeout_seconds": timeout_seconds,
        }
        return wrapped, environment, evidence


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("doctor", "validate-profile"))
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)
    manager = SandboxManager()
    if args.command == "doctor":
        result = manager.doctor()
    else:
        if not args.profile:
            parser.error("validate-profile requires --profile")
        _, digest = load_profile(args.profile)
        result = {"valid": True, "profile_sha256": digest, "enforcement_ready": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if args.command == "validate-profile" or result["enforcement_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
