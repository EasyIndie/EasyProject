# M4 — Agent Sandbox & Runtime Security

## Goal

Introduce OS-enforced, task-scoped isolation so multiple cooperating Agents cannot read or mutate each other's workspaces, stable source, host credentials, control-plane state or unauthorized network resources.

## Current baseline

- Git Worktrees isolate source trees from accidental edits but do not restrict process access to the host.
- `scripts/agent-run.py` is a process dispatcher, not a sandbox.
- Codex has an OS-enforced sandbox mode; Claude Code's Bash sandbox does not cover all built-in tools and helpers.
- Pi's tool allowlist is not a security boundary. The current Evolution path automatically adds `harness_options.pi_unsandboxed_write=true`, which is not genuine human opt-in and must be removed in M4.1.
- The repository has task orchestration, approval artifacts, cancellation and review evidence, but no OS-enforced universal backend or artifact broker.

## Work breakdown

| ID | Deliverable | Exit criteria |
|---|---|---|
| M4.0 | Sandbox Contract + architecture | Versioned JSON Schema, threat model, trust-zone and fail-closed rules |
| M4.1 | Pi unsafe-write correction | Generated tasks never auto-authorize; explicit CLI override; regression tests; default refusal |
| M4.2a | Launcher contract | Backend interface, profile validation, capability doctor, handoff enforcement evidence, fail-closed Runner integration |
| M4.3 | Artifact Broker | Immutable export/import, path/symlink/type/size validation, no shared writable workspace |
| M4.4 | Linux OCI backend | Rootless runtime, namespaces, seccomp, LSM, resource limits, network deny, conformance suite |
| M4.5 | Strong isolation backends | gVisor/Kata/Firecracker plugin interface and documented deployment profiles |
| M4.6 | Brokers and audit | Scoped credential/network broker, policy hash, denial evidence, operational guide |

## Execution order

M4.0 is documentation and schema only. M4.1 is merged. M4.2a defines the backend interface and fail-closed launch path, but does not provide OS enforcement. M4.2b adds a real host backend and must not be marked complete until process-tree tests prove that file tools, shell tools, MCP/hooks and descendants share the boundary. M4.3 can be developed independently after the immutable artifact contract is agreed. Linux backend work follows the broker and policy interfaces.

## Explicit non-goals

- Do not merge Agent branches automatically.
- Do not expose host credentials to make CLI authentication convenient.
- Do not treat Worktree, tool allowlist, prompt instruction, environment proxy variables or JSON policy alone as a sandbox.
- Do not claim CI schema tests prove kernel-level enforcement.
- Do not add privileged Docker daemon access to an Agent.
