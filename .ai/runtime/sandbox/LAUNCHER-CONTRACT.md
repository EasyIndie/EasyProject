# Sandbox Launcher Contract (M4.2)

## Status

The repository now includes a Linux Rootless Podman backend and a conservative capability probe. A host is enforcement-ready only when rootless mode, subordinate UID/GID mappings, cgroup v2, systemd delegation, and cpu/memory/pids controllers are verified. Other platforms remain unavailable. Unit tests do not prove kernel enforcement; dedicated Linux conformance tests are still required. A Worktree, Agent permission mode, or tool allowlist is not isolation.

## Execution invariant

The launcher receives the complete harness argv and starts the harness as its child inside one boundary. All descendants—including shell commands, built-in file tools, MCP servers, hooks, language servers and extensions—must remain subject to that boundary. A backend that only wraps Bash is insufficient.

A backend is eligible only if it can enforce workspace-only filesystem access, default-deny network, process-tree inheritance and termination, CPU/memory/PID/wall-clock limits, no privilege escalation, no host runtime socket, and a sanitized launcher environment. Egress proxy and scoped-secret broker capabilities are mandatory when requested by the profile. Failure during setup aborts before the Agent starts.

## Linux Rootless Podman

The implementation is in `scripts/sandbox_backends/podman_rootless.py`. It requires rootless Podman, subordinate UID/GID mappings, cgroup v2, systemd cgroup manager and delegated cpu/memory/pids controllers. It uses a digest-pinned image already present locally (`--pull=never`), private namespaces, `--network=none`, read-only rootfs, dropped capabilities, no-new-privileges, a single task workspace mount, private tmpfs and explicit resource limits.

Worktree `.git` pointer files are rejected because they refer to shared Git metadata outside the task. Use an independent clone or a patch-only workflow. The backend does not implement egress proxy or credential brokering; requests requiring either are rejected by backend selection.

## Verification boundary

Unit tests prove policy selection, argv construction and fail-closed behavior only. They do not prove namespaces, seccomp, filesystem isolation, network isolation or effective cgroup enforcement. M4.4.4 requires a dedicated Linux worker conformance suite. Do not describe the backend as production-ready until that suite passes.

## CLI

```bash
python3 scripts/sandbox_runtime.py doctor
python3 scripts/sandbox_runtime.py validate-profile --profile .ai/runtime/examples/sandbox-profile.json
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --worktrees --require-sandbox
```

Exit code 3 from `doctor` means no backend can enforce the complete policy. This is fail-closed status, not a runtime failure to ignore.
