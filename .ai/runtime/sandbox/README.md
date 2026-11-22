# Sandbox Runtime Architecture (M4)

## Status and scope

This document defines the target security architecture for multi-agent execution. The Sandbox Profile schema is a policy contract, **not an enforcement mechanism**. Until a platform backend is implemented and its conformance tests pass, a task must not be described as sandboxed merely because it has a Git Worktree or a profile JSON file.

The security boundary is one **Agent Task execution**, not an Agent role and not a Git Worktree. Every process started by an untrusted Agent—including shell commands, file tools, MCP servers, hooks, language servers, and descendants—must either run inside the same enforced boundary or be treated as a separately privileged service.

## Threat model

Protect, by default:

- stable checkout, candidate controller, orchestrator state, and approval evidence;
- every other task's workspace and private caches;
- user home, SSH keys, cloud credentials, CLI auth stores, browser profiles, and host environment secrets;
- host management interfaces, Docker/container runtime sockets, LAN services, and unapproved Internet destinations;
- host processes, devices, kernel interfaces, and resource availability;
- the policy engine, broker, audit records, and trusted integrator from Agent modification.

Assume repository content, issues, generated artifacts, model output, dependencies, and tool output may be malicious. A sandbox reduces the impact of compromise; it does not make model output trustworthy or replace review.

Out of scope for the initial local runtime: protection against a malicious host administrator, physical attacks, all hardware side channels, or vulnerabilities in the host kernel/hypervisor. High-risk multi-tenant execution should use a VM-backed backend.

## Architecture

```text
Human / CI policy
      |
      v
Orchestrator ---- Approval store (outside task sandbox)
      |
      v
Sandbox Manager ---- platform backend (native / OCI / gVisor / VM)
      |                              |
      |                         Agent Task A
      |                         Agent Task B
      v
Artifact Broker <---- validated, immutable exports
      |
      v
Read-only Reviewer / trusted Integrator
      |
      v
Candidate branch -> separately approved PR
```

### Trust zones

1. **Control plane**: Orchestrator, policy resolver, approval records, broker, audit log. Never mounted writable into an Agent sandbox.
2. **Task plane**: one isolated execution per task. Own workspace, process tree, private temporary directory and cache. No shared writable paths.
3. **Artifact plane**: broker validates and transfers declared outputs. No direct task-to-task filesystem sharing.
4. **Integration plane**: trusted process validates patch paths, symlinks, file types, size, base revision and checks before applying changes. Agents cannot write stable checkout or merge/push/deploy.

### Sandbox Profile

See [sandbox-profile.schema.json](../schemas/sandbox-profile.schema.json). The profile is declarative and versioned. Policy resolution is performed by the trusted control plane. An Agent may request capabilities but cannot expand its own profile. Missing backend, unsupported policy, setup failure, or enforcement uncertainty must fail closed.

The profile must constrain:
- filesystem: task workspace only; stable checkout, other task workspaces, shared Git metadata/object/ref stores, home, credentials and control-plane runtime denied;
- process: process-tree inheritance, timeout, CPU/memory/process limits, no privilege escalation;
- network: deny by default, no LAN/host routes, explicit brokered egress only;
- secrets: no host environment inheritance or credential mounts; scoped short-lived broker grants only;
- artifacts: explicit export allowlist, no direct workspace sharing, reject path traversal and escaping symlinks.

## Backend strategy

| Platform | Initial backend | Stronger backend | Important limitation |
|---|---|---|---|
| macOS | Seatbelt/native process sandbox, with harness-specific gaps closed by wrapping the entire harness | VM-backed remote worker | Docker Desktop is a Linux VM; bind mounts still expose mounted host paths |
| Linux | Rootless OCI container + user/PID/mount/network namespaces + seccomp + AppArmor/SELinux | gVisor or Kata; Firecracker for high-risk workloads | Ordinary containers share the host kernel; rootless alone is not a complete sandbox |
| Windows | AppContainer or a dedicated restricted execution backend | Hyper-V isolated VM / WSL2 Linux worker | Claude Code's documented local Bash sandbox currently lists WSL2, not native Windows; harness support must be verified per version |
| Cloud Linux | Rootless OCI | gVisor/Kata/Firecracker | Multi-tenant workloads require stronger isolation, patching and monitoring |

No backend is assumed available merely because its CLI is installed. The backend must report the effective policy and pass conformance tests.

## Agent adapter requirements

- **Codex**: use its OS sandbox as defense in depth, but do not assume workspace-write blocks reads of sensitive files outside the workspace. The outer task boundary remains authoritative.
- **Claude Code**: its Bash sandbox does not cover built-in Read/Edit/Write, MCP servers, hooks, LSP and other helper processes. Run the entire Claude process and its helpers inside the outer boundary; disable unsandboxed retries and excluded commands.
- **Pi**: tool allowlists are not OS isolation. Pi must run inside the outer task boundary. Until that backend is available, write-enabled Pi tasks are unsupported by default and require a separately reviewed explicit unsafe override; a Worktree is not a security boundary.

Never silently fall back to unsandboxed execution. Do not pass host credential directories, host Docker sockets, or the full host environment into task containers.

## Collaboration and artifact flow

- One task = one sandbox, one private writable workspace, one process/resource budget.
- Parallel Agents receive separate snapshots/worktrees and separate caches.
- Planner and Reviewer are read-only. Developer may write only to its task workspace.
- Agents exchange structured Handoff, diff/patch, test report and review evidence through the Artifact Broker.
- Broker rejects absolute paths, parent traversal, escaping symlinks, special files, oversized artifacts and undeclared outputs.
- Reviewer receives an immutable snapshot of the exact proposed revision, not a live Developer workspace.
- Only the trusted Integrator may apply an approved patch to the candidate branch.

## Credential and network brokers

Agents receive no long-lived host credentials. A broker may perform narrowly scoped operations such as fetching dependencies or creating a pull request after approval. Grants are bound to task ID, operation, resource and expiry; raw tokens are never returned to the Agent.

Network isolation must be enforced below the Agent tool layer. Environment variables such as HTTP_PROXY are not a security boundary. Deny LAN, loopback-to-host management endpoints, metadata services, and arbitrary egress. DNS and IPv6 must follow the same policy.

## Conformance and audit

A backend is not production-ready until tests demonstrate denial of:
- stable checkout and another task's workspace reads/writes;
- home, SSH, cloud and Agent credential reads;
- Docker/container socket and host management endpoint access;
- LAN, metadata service and unapproved Internet access;
- child-process attempts to bypass each restriction;
- profile modification, sandbox disablement and unsandboxed retry;
- timeout/cancellation leaving background descendants alive;
- artifact path traversal, symlink escape, special files and oversized exports.

Record backend/version, host OS, effective profile hash, task ID, start/end, exit/termination reason, resource usage, policy denials and artifact digests. Do not record secret values.

## Backend selection

See [ADR-001: Production Sandbox Backend Selection](ADR-001-backend-selection.md) for the platform decision, Linux Rootless Podman prerequisites, macOS Seatbelt limitations, isolated Git metadata requirement and Credential/Network Broker dependency.

## Launcher implementation status

The current launcher contract is implemented in `scripts/sandbox_runtime.py`. The Orchestrator accepts the trusted control-plane switch `--require-sandbox` (default profile: the stable checkout's `.ai/runtime/examples/sandbox-profile.json`) and passes it to every Agent Runner. The Agent Runner accepts `--require-sandbox --sandbox-profile <file>` and refuses to start when no complete backend is registered. Its handoff records `sandbox_status`, backend ID and profile digest. Legacy runs without `--require-sandbox` are explicitly marked `not-enforced`; they are not considered isolated.

The backend interface also requires a sanitized process environment and must cap the outer Runner timeout to the profile's timeout. A host environment copy is not an acceptable sandbox launch environment.

The backend registry currently has no production implementation. `python3 scripts/sandbox_runtime.py doctor` therefore exits with status 3 and reports `enforcement_ready: false`. This is the correct safe state until an OS backend and its conformance suite are merged.

See [LAUNCHER-CONTRACT.md](LAUNCHER-CONTRACT.md) for the interface and backend acceptance requirements.

## Delivery milestones

1. M4.0: contract, threat model, trust zones and security invariants (this change).
2. M4.1: remove implicit Pi unsafe-write acknowledgement; add explicit unsafe override that is never selected by generated tasks.
3. M4.2: adapter enforcement contract and whole-process launch boundary; verify current Codex/Claude CLI capabilities.
4. M4.3: artifact broker and immutable cross-agent handoff.
5. M4.4: Linux Rootless OCI backend and executable conformance tests.
6. M4.5: gVisor/Kata/Firecracker backends after baseline conformance.
7. M4.6: credential and network brokers; audit evidence and operational hardening.

## Acceptance criteria

- Every task declares a versioned Sandbox Profile.
- A profile cannot grant access to stable checkout, other task workspaces, host credentials, host runtime sockets or LAN by default.
- Policy is resolved and enforced by a trusted backend, not by model instructions or tool allowlists.
- Unsupported or unavailable enforcement fails closed.
- Cross-agent collaboration uses brokered immutable artifacts.
- Conformance tests run in CI for deterministic contract checks and on each supported host for actual OS enforcement.
- Documentation distinguishes policy intent, backend enforcement and locally verified behavior.
