# M4 — Agent Sandbox & Runtime Security

## Goal

Introduce OS-enforced, task-scoped isolation so multiple cooperating Agents cannot read or mutate each other's workspaces, stable source, host credentials, control-plane state or unauthorized network resources.

## Current baseline

- Git Worktrees isolate source trees from accidental edits but do not restrict process access to the host.
- `scripts/agent-run.py` is a process dispatcher, not a sandbox.
- Codex has an OS-enforced sandbox mode; Claude Code's Bash sandbox does not cover all built-in tools and helpers.
- Pi's tool allowlist is not a security boundary. The current Evolution path automatically adds `harness_options.pi_unsandboxed_write=true`, which is not genuine human opt-in and must be removed in M4.1.
- The repository has task orchestration, approval artifacts, cancellation and review evidence. The Linux Rootless Podman launcher is now implemented behind a fail-closed capability probe; kernel-level conformance is still pending.

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
| M4.4.3 | Git metadata isolation | Reject shared worktree pointer metadata; move toward independent task clones or patch-only Agent workspaces |
| M4.4.4 | Linux conformance suite | Prove filesystem, network, process-tree and effective resource enforcement on a dedicated Linux worker |
| M4.5 | Strong isolation backends | gVisor/Kata/Firecracker plugin interface and documented deployment profiles |
| M4.6 | Brokers and audit | Scoped credential/network broker, policy hash, denial evidence, operational guide |

## Backend decision

The platform selection and prerequisites are recorded in [ADR-001: Production Sandbox Backend Selection](../../.ai/runtime/sandbox/ADR-001-backend-selection.md). Linux Rootless Podman is the primary full-profile backend; macOS Seatbelt is a possible weaker local profile, not a full-profile substitute. The first Linux backend must also solve shared Git metadata isolation and use a pinned runtime image. Hosted-model credentials remain blocked until M4.6.

## Execution order

M4.0 is documentation and schema only. M4.1 is merged. M4.2a defines the backend interface and fail-closed launch path, but does not provide OS enforcement. M4.2b records the platform decision. M4.3a/b artifact exchange is complete. M4.4.1/4.4.2 now provide a conservative Rootless Podman probe and launcher, but M4.4 remains incomplete until independent Git metadata handling and dedicated Linux kernel-conformance tests pass. The backend deliberately does not support network egress or credential brokering; those remain M4.6 work.

## Explicit non-goals

- Do not merge Agent branches automatically.
- Do not expose host credentials to make CLI authentication convenient.
- Do not treat Worktree, tool allowlist, prompt instruction, environment proxy variables or JSON policy alone as a sandbox.
- Do not claim CI schema tests prove kernel-level enforcement.
- Do not add privileged Docker daemon access to an Agent.
