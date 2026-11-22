# M4 — Agent Sandbox & Runtime Security

## Goal

Introduce OS-enforced, task-scoped isolation so multiple cooperating Agents cannot read or mutate each other's workspaces, stable source, host credentials, control-plane state or unauthorized network resources.

## Current baseline

- Git Worktrees isolate source trees from accidental edits but do not restrict process access to the host.
- scripts/agent-run.py is a process dispatcher, not a sandbox.
- Pi's tool allowlist is not a security boundary. Unsafe Pi writes require explicit opt-in or a mandatory OS sandbox.
- The repository has task orchestration, approval artifacts, cancellation and review evidence. The Linux Rootless Podman launcher is implemented behind a fail-closed capability probe; kernel-level conformance is still pending.
- Sandbox-required task workspaces now use independent Git clones instead of linked Git Worktrees, keeping shared Git metadata outside the container boundary.

## Work breakdown

| ID | Deliverable | Exit criteria |
|---|---|---|
| M4.0 | Sandbox Contract + architecture | Versioned JSON Schema, threat model, trust-zone and fail-closed rules |
| M4.1 | Pi unsafe-write correction | Generated tasks never auto-authorize; explicit CLI override; regression tests; default refusal |
| M4.2a | Launcher contract | Backend interface, profile validation, capability doctor, handoff enforcement evidence, fail-closed Runner integration |
| M4.2b | Backend decision | Accepted platform ADR; Linux Rootless Podman selected for full profile; shared Git metadata and credential-broker dependencies documented |
| M4.3a | Artifact Broker core | Content-addressed export, manifest/hash verification, read-only reviewer materialization, path/symlink/type/size validation |
| M4.3b | Artifact Broker integration | Sandbox-required Orchestrator exports immutable review artifacts after Agent and checks exit; approval and Integrator verify task/base/fingerprint binding |
| M4.4.1 | Rootless Podman capability probe | Verify rootless mode, subordinate UID/GID mappings, cgroup v2, systemd delegation and cpu/memory/pids controllers |
| M4.4.2 | Rootless OCI launcher | Pinned image, network none, namespaces, read-only rootfs, workspace-only mount, limits, sanitized Agent environment |
| M4.4.3 | Independent Git metadata | Sandbox-required tasks use independent clones; reject shared Git common-dir and object alternates; Integrator imports reviewed commits explicitly |
| M4.4.4 | Linux conformance suite | Prove filesystem, network, process-tree and effective resource enforcement on a dedicated Linux worker |
| M4.5 | Strong isolation backends | gVisor/Kata/Firecracker plugin interface and documented deployment profiles |
| M4.6 | Brokers and audit | Scoped credential/network broker, policy hash, denial evidence, operational guide |

## Backend decision

The platform selection and prerequisites are recorded in [ADR-001: Production Sandbox Backend Selection](../../.ai/runtime/sandbox/ADR-001-backend-selection.md). Linux Rootless Podman is the primary full-profile backend; macOS Seatbelt is a possible weaker local profile, not a full-profile substitute. Hosted-model credentials remain blocked until M4.6.

## Execution order

M4.0–M4.3 are complete. M4.4.1/4.4.2 provide a conservative Rootless Podman probe and launcher. M4.4.3 switches sandbox-required tasks to independent Git clones and explicitly transfers approved commits into the trusted repository during integration. M4.4 remains incomplete until M4.4.4 proves filesystem, network, process-tree and effective cgroup enforcement on a dedicated Linux worker. The backend deliberately does not support network egress or credential brokering; those remain M4.6 work.

## Explicit non-goals

- Do not merge Agent branches automatically.
- Do not expose host credentials to make CLI authentication convenient.
- Do not treat Worktree, tool allowlist, prompt instruction, environment proxy variables or JSON policy alone as a sandbox.
- Do not claim CI schema tests prove kernel-level enforcement.
- Do not add privileged Docker daemon access to an Agent.
