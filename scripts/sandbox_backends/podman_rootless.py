#!/usr/bin/env python3
"""Conservative Linux Rootless Podman backend for task-scoped Agent sandboxes."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import json
from pathlib import Path
from typing import Sequence
from sandbox_runtime import SandboxCapabilities, SandboxEnforcementError, SandboxLaunchSpec

PINNED_IMAGE = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
REQUIRED = {"cpu", "memory", "pids"}

class RootlessPodmanBackend:
    backend_id = "linux-rootless-oci"

    def __init__(self, podman: str | None = None) -> None:
        self.podman = podman or shutil.which("podman") or "podman"

    @staticmethod
    def _host_environment() -> dict[str, str]:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(Path.home()),
            "LANG": "C",
            "LC_ALL": "C",
        }
        for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
            if os.environ.get(key):
                env[key] = os.environ[key]
        return env

    @staticmethod
    def _delegated_controllers() -> tuple[set[str], str]:
        root_file = Path("/sys/fs/cgroup/cgroup.controllers")
        if not root_file.is_file():
            return set(), "cgroup v2 is unavailable"
        try:
            root = set(root_file.read_text().split())
        except OSError as exc:
            return set(), f"cannot read cgroup controllers: {exc}"
        if not REQUIRED.issubset(root):
            return root, "host lacks cpu/memory/pids controllers"
        systemctl = shutil.which("systemctl")
        if not systemctl:
            return set(), "systemctl unavailable; delegation cannot be verified"
        try:
            result = subprocess.run(
                [systemctl, "--user", "show", "--property=ControlGroup", "--value"],
                text=True, capture_output=True, check=False, timeout=5,
                env=RootlessPodmanBackend._host_environment(),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return set(), f"cannot inspect user cgroup: {exc}"
        rel = result.stdout.strip()
        if result.returncode or not rel.startswith("/"):
            return set(), "systemd user service cgroup is unavailable"
        cgroup = Path("/sys/fs/cgroup") / rel.lstrip("/")
        try:
            available = set((cgroup / "cgroup.controllers").read_text().split())
            enabled = set((cgroup / "cgroup.subtree_control").read_text().replace("+", "").split())
        except OSError as exc:
            return set(), f"user cgroup delegation is unreadable: {exc}"
        effective = enabled
        if not REQUIRED.issubset(effective):
            return effective, "cpu/memory/pids are not delegated to the user service"
        return effective, "required systemd user cgroup controllers verified"

    def probe(self) -> SandboxCapabilities:
        failures: list[str] = []
        if not Path("/proc/self/uid_map").is_file():
            failures.append("Linux UID namespace mapping is unavailable")
        if not shutil.which(self.podman):
            failures.append("Podman executable is unavailable")
        info: dict = {}
        if not failures:
            try:
                result = subprocess.run(
                    [self.podman, "info", "--format", "json"],
                    text=True, capture_output=True, check=False, timeout=8,
                    env=self._host_environment(),
                )
                if result.returncode:
                    failures.append("podman info failed: " + result.stderr.strip())
                else:
                    info = json.loads(result.stdout)
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                failures.append(f"cannot inspect Podman: {exc}")
        host = info.get("host", {}) if info else {}
        if info and host.get("security", {}).get("rootless") is not True:
            failures.append("Podman is not rootless")
        if info and host.get("cgroupVersion") != "v2":
            failures.append("Podman is not using cgroup v2")
        if info and host.get("cgroupManager") != "systemd":
            failures.append("Podman is not using systemd cgroups")
        maps = host.get("idMappings", {}) if info else {}
        uidmap = maps.get("uidmap", []) if isinstance(maps, dict) else []
        gidmap = maps.get("gidmap", []) if isinstance(maps, dict) else []
        if info and (not uidmap or not gidmap or
                     not any(int(x.get("size", 0)) > 1 for x in uidmap + gidmap)):
            failures.append("subordinate UID/GID mappings are missing")
        controllers, reason = self._delegated_controllers()
        if not REQUIRED.issubset(controllers):
            failures.append(reason)
        ready = not failures
        return SandboxCapabilities(
            backend_id=self.backend_id, platform="linux", available=ready,
            enforces_filesystem=ready, enforces_network=ready,
            isolates_process_tree=ready, terminates_process_tree_on_exit=ready,
            enforces_resource_limits=ready, supports_egress_proxy=False,
            supports_secrets_broker=False, status="ready" if ready else "unavailable",
            reason="; ".join(failures) if failures else
                   "rootless Podman, subordinate ID maps and delegated cgroup v2 verified",
        )

    def build_environment(self, spec: SandboxLaunchSpec) -> dict[str, str]:
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "")
        if not runtime_dir or not Path(runtime_dir).is_dir():
            raise SandboxEnforcementError("XDG_RUNTIME_DIR is unavailable.")
        return {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(Path.home()), "XDG_RUNTIME_DIR": runtime_dir,
            "LANG": "C", "LC_ALL": "C",
        }

    def build_command(self, command: Sequence[str], spec: SandboxLaunchSpec) -> list[str]:
        if not command or any(not isinstance(arg, str) for arg in command):
            raise SandboxEnforcementError("Agent command must be a non-empty argv.")
        runtime = spec.profile.get("runtime", {})
        image = runtime.get("image", "")
        if runtime.get("backend") != self.backend_id or not PINNED_IMAGE.fullmatch(image):
            raise SandboxEnforcementError("runtime.image must be pinned by sha256 digest.")
        workspace = spec.workspace
        if not workspace.is_dir() or workspace.is_symlink():
            raise SandboxEnforcementError("Workspace must be an existing real directory.")
        if "," in str(workspace):
            raise SandboxEnforcementError("Workspace path cannot contain commas in Podman mount syntax.")
        git = workspace / ".git"
        if git.is_symlink() or git.is_file():
            raise SandboxEnforcementError("Git worktree pointer or symlink detected; shared Git metadata is forbidden.")
        if not git.is_dir():
            raise SandboxEnforcementError("Sandbox workspace requires a private .git directory.")
        if (git / "commondir").exists() or (git / "objects/info/alternates").exists():
            raise SandboxEnforcementError("Shared Git common directory or object alternates are forbidden.")
        fs = spec.profile["filesystem"]
        if not fs["workspace_read"]:
            raise SandboxEnforcementError("Workspace read access is required.")
        process = spec.profile["process"]
        memory = int(process["max_memory_mb"])
        cpu = float(process["max_cpu"])
        pids = int(process["max_processes"])
        if memory < 128 or cpu <= 0 or pids < 1 or spec.timeout_seconds < 1:
            raise SandboxEnforcementError("Invalid effective resource limits.")
        mode = "rw" if fs["workspace_write"] else "ro"
        uid, gid = os.getuid(), os.getgid()
        return [
            self.podman, "run", "--rm", "--init", "--pull=never",
            "--userns=keep-id", f"--user={uid}:{gid}",
            "--network=none", "--pid=private", "--ipc=private", "--cgroupns=private",
            "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
            f"--pids-limit={pids}", f"--memory={memory}m", f"--cpus={cpu:g}",
            "--stop-timeout=5", "--ulimit=core=0",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=256m",
            "--tmpfs", "/home/sandbox:rw,noexec,nosuid,nodev,size=64m",
            # The task clone has private Git metadata (no shared refs/objects/remotes).
            # Keep it writable so the Agent can create the commit consumed by Integrator.
            # The entire clone remains inside this task sandbox and cannot reach stable refs.
            "--mount", f"type=bind,src={workspace},dst=/workspace,{mode}",
            "--workdir=/workspace",
            "--env=PATH=/usr/local/bin:/usr/bin:/bin",
            "--env=HOME=/home/sandbox", "--env=TMPDIR=/tmp",
            "--env=LANG=C.UTF-8", "--env=LC_ALL=C.UTF-8", "--env=CI=1",
            "--env=GIT_OPTIONAL_LOCKS=0", "--env=GIT_CONFIG_NOSYSTEM=1",
            "--env=GIT_CONFIG_GLOBAL=/dev/null", "--env=GIT_TERMINAL_PROMPT=0",
            image, *command,
        ]
