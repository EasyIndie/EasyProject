# Sandbox Launcher Contract (M4.2)

## Status

This change adds the backend interface, policy validation, capability reporting and fail-closed integration point. **It does not ship a production OS-enforcement backend.** On all hosts, `doctor` must currently report `enforcement_ready: false`. This is expected and must not be worked around by treating a Worktree, Agent permission mode, or tool allowlist as isolation.

## Execution invariant

The launcher receives the complete harness argv and starts the harness as its child inside one boundary. All descendants—including shell commands, built-in file tools, MCP servers, hooks, language servers and extensions—must remain subject to that boundary. A backend that only wraps Bash is insufficient.

A backend is eligible only if it can enforce all of the following for the requested profile:

- workspace-only filesystem access, including denial of stable checkout, other task workspaces, user home, credentials and control-plane runtime;
- default-deny network, no host/LAN access, and explicit egress proxy policy;
- process-tree inheritance and reliable termination;
- CPU, memory, process-count and wall-clock limits;
- no privilege escalation and no host container-runtime socket;
- effective-policy evidence (backend/version, profile digest and platform);
- sanitized launcher environment: never inherit the host environment wholesale;
- egress proxy and scoped-secret broker capabilities when the profile requests them;
- profile wall-clock timeout must cap the Runner timeout.

The manager rejects partial backends. A backend must not claim support based on a binary being installed; `probe()` must verify prerequisites needed to enforce the actual policy. Failure during setup aborts before the Agent starts.

## Python interface

Implemented in `scripts/sandbox_runtime.py`:

- `SandboxBackend.probe() -> SandboxCapabilities`
- `SandboxBackend.build_command(command, spec) -> argv`
- `SandboxBackend.build_environment(spec) -> minimal env`
- `SandboxManager.doctor()`
- `SandboxManager.build_command(...)`
- `load_profile(path)`

Backends are injected into the manager by trusted application code. A backend must provide both a wrapped argv and a minimal environment; returning `os.environ.copy()` or forwarding host credential variables violates the contract. Task JSON and Agent-controlled configuration cannot register a backend, choose an arbitrary launcher executable, or relax a profile. Task permissions are intersected with the trusted maximum profile: they may narrow workspace read/write, network and brokered-secret access, but cannot expand any of them.

## CLI

```bash
python3 scripts/sandbox_runtime.py doctor
python3 scripts/sandbox_runtime.py validate-profile --profile .ai/runtime/examples/sandbox-profile.json
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --worktrees --require-sandbox
```

Exit code 3 from `doctor` means no production backend can enforce the complete policy. This is a fail-closed status, not a runtime failure to be ignored.

## Agent Runner

`agent-orchestrate.py --require-sandbox --worktrees` is the trusted control-plane switch; sandbox-required runs refuse a shared stable checkout. The Orchestrator pins the profile path and digest in the external run journal and passes the requirement to every Runner invocation. A resume must preserve the requirement and exact profile digest. Direct `agent-run.py --require-sandbox --sandbox-profile <file>` requests mandatory enforcement. If no complete backend is registered, it exits before spawning Pi, Codex or Claude Code. Without `--require-sandbox`, legacy local execution remains explicitly unsandboxed and is not to be described as secure or isolated. New unattended or untrusted execution flows must pass `--require-sandbox`.

## Backend implementation sequence

1. macOS Seatbelt: launch the entire harness process tree, explicit file rules, deny network by default, verify effective policy. Do not rely on Codex's internal command sandbox as a wrapper around Claude/Pi.
2. Linux Rootless OCI: user/mount/PID/network namespaces, read-only root, no-new-privileges, seccomp, LSM, cgroup limits, no Docker socket.
3. Windows: AppContainer or dedicated VM/WSL2 worker; verify each harness's support and process inheritance.
4. Stronger remote backend: gVisor/Kata/Firecracker for hostile multi-tenant workloads.

## Verification boundary

Unit tests for this contract use a fake backend and prove selection, sanitized-environment handoff and fail-closed behavior only. They do not prove Seatbelt, namespaces, seccomp, filesystem isolation, network isolation or kernel enforcement. Those claims require backend-specific conformance tests on the supported host OS.
