# ADR-001: Production Sandbox Backend Selection

- **Status:** Accepted
- **Date:** 2026-11-22
- **Scope:** M4.2b and M4.4
- **Decision owners:** EasyProject runtime maintainers

## Context

M4.2a provides a fail-closed backend interface. M4.3a/b provides immutable review artifacts and only publishes them after a sandbox-required task and its acceptance checks have completed. No production backend is registered yet.

The default Sandbox Profile requires filesystem and network isolation, process-tree inheritance and cleanup, CPU/memory/process limits, and a sanitized environment. A backend must prove the complete requested policy; detecting a CLI executable is not proof of enforcement.

## Decision

### 1. Linux Rootless OCI is the primary full-profile backend

Implement **Rootless Podman** first for Linux workers. A backend is eligible only when its runtime probe confirms all of the following:

- Podman is running rootless for the current unprivileged user; no rootful socket or privileged fallback.
- User namespaces are usable and the worker has valid subordinate UID/GID mappings in `/etc/subuid` and `/etc/subgid` (normally at least 65,536 IDs).
- cgroup v2 is active and the required controllers are actually delegated to the user service. CPU, memory and PID limits must be verified from the effective cgroup, not inferred from accepted CLI flags.
- The container uses a private PID namespace, `--network=none`, a read-only root filesystem, `no-new-privileges`, all capabilities dropped, a PID limit, memory/CPU limits and a private temporary filesystem.
- Only the task workspace and explicitly brokered resources are mounted. Never mount the host home, credentials, control-plane runtime, another task workspace, shared Git metadata, or the Podman/Docker socket.
- Container shutdown terminates every descendant before the launcher reports completion.

Podman documents rootless user-namespace prerequisites and cgroup-v2 resource-limit behavior. In particular, rootless resource limits are not available on cgroup v1. See the [Podman rootless guide](https://github.com/podman-container-tools/podman/blob/main/rootless.md) and [podman run reference](https://docs.podman.io/en/latest/markdown/podman-run.1.html).

Docker Rootless is a possible alternative backend, not an implicit fallback. Its resource flags require cgroup v2 and systemd, and controller delegation must be verified. See [Docker Rootless mode](https://docs.docker.com/engine/security/rootless/) and [Rootless troubleshooting / limitations](https://docs.docker.com/engine/security/rootless/troubleshoot/).

### 2. macOS Seatbelt is not the full-profile backend

Seatbelt can provide useful kernel-enforced filesystem, network and process restrictions around a complete command tree. However, the public `sandbox-exec` entry point is deprecated, and Seatbelt does not provide cgroup-style per-task CPU, memory and PID quotas.

OpenAI documents that Codex uses Seatbelt through `/usr/bin/sandbox-exec`, while also noting Apple's deprecation warning and the complexity of SBPL policy generation. See [Inside the Codex sandbox](https://openai.com/index/inside-the-codex-sandbox/).

Therefore:

- Do not mark a macOS Seatbelt-only backend as satisfying the default profile while `resource_limits=true`.
- A future explicitly weaker local profile may use Seatbelt for trusted, low-risk or offline tasks, but it must disclose the missing resource controls and must never be silently upgraded to the full profile.
- Probe the actual `sandbox-exec` behavior and run the macOS conformance suite on macOS. Do not infer support from the binary's presence.

### 3. Windows is deferred

Use a dedicated Linux worker through WSL2 or a remote worker for the first complete implementation. Do not treat WSL2 as an equivalent boundary without testing the Windows host filesystem, interop, process and network escape surfaces. A native AppContainer backend requires a separate conformance suite.

### 4. Stronger isolation remains a later tier

For hostile multi-tenant workloads, evaluate gVisor, Kata Containers or Firecracker after the Rootless OCI contract is stable. Ordinary containers still share the host kernel and are not equivalent to a VM boundary.

## Required architecture changes before M4.4 can run Agent tasks

### A. Isolated Git metadata

The current task worktrees are Git worktrees whose `.git` pointer references shared repository metadata. The profile explicitly denies `shared_git_metadata`; therefore a sandbox must not mount the shared Git common directory just to make Git commands work.

Before enabling a container backend for coding tasks, choose one of:

1. create an independent per-task clone with a private object database and private refs; or
2. provide a private task Git directory while exposing only immutable shared objects read-only, with a tested write boundary; or
3. remove Git metadata from the Agent sandbox and make the trusted host-side Artifact Broker / Integrator the only Git-aware layer.

The first implementation should prefer an independent clone or the third option. The Agent must not be able to write shared refs, indexes, objects or hooks.

### B. Agent runtime image and credentials

The backend must use a trusted image pinned by digest, containing the approved harness runtime and required dependencies. Do not mount host-installed CLI package directories if they overlap user configuration or credentials.

The current network policy is default-deny. Codex, Claude Code and Pi generally need model-service access, but passing raw host API keys or OAuth files into the Agent would expose credentials to the model process. Real hosted-model execution therefore depends on the separate Credential/Network Broker milestone (M4.6). Until then, the container backend can run conformance fixtures and offline workloads, but must not claim that hosted Agent execution is ready.

## M4.4 implementation checklist

1. Add a Rootless Podman backend with an explicit pinned image requirement.
2. Probe rootless mode, subordinate UID/GID mappings, cgroup v2, systemd delegation and required controllers.
3. Build an OCI command with private PID/network namespaces, read-only root, no-new-privileges, cap drop, workspace-only mounts, tmpfs and enforced CPU/memory/PID limits.
4. Return a minimal environment; never pass through the host environment.
5. Ensure container teardown kills all descendants before the workspace is frozen.
6. Add Linux conformance tests for stable checkout, other workspaces, shared Git metadata, host home, credentials, runtime directory, container socket, LAN/public network, process escape and effective cgroup limits.
7. Make unsupported prerequisites fail closed. No rootful Docker fallback, no host network, no privileged container and no warning-only resource limits.
8. Wire the independent-clone / artifact integration path before enabling coding tasks.

## Consequences

- The user's Apple Silicon Mac remains a lightweight control plane; full isolation runs on a Linux worker rather than one VM per Agent.
- A low-cost VPS is not automatically suitable: it must expose rootless user namespaces, cgroup v2 and delegated controllers.
- The current backend registry intentionally remains empty until the above conditions are implemented and tested.
