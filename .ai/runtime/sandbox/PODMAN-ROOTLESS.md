# Linux Rootless Podman Backend (M4.4.1–M4.4.4)

This backend is intentionally narrow: Linux, rootless Podman, cgroup v2, systemd user-service delegation, and delegated cpu/memory/pids controllers. It refuses rootful Podman, cgroup v1, missing subordinate UID/GID mappings, missing resource controllers, mutable image tags, and shared Git worktree metadata.

## Runtime image

Every profile must set runtime.backend=linux-rootless-oci and an immutable OCI reference of the form registry/name@sha256:<64 lowercase hex>. The image must already exist in rootless Podman's local image store; launch uses --pull=never. The example uses a syntactically valid placeholder digest only; it is not a published or verified image.

## Launch boundary

The launcher applies rootless user namespaces, private PID/network/IPC/cgroup namespaces, network=none, read-only container root, dropped capabilities, no-new-privileges, private tmpfs mounts, one task-workspace bind mount, a separate read-only .git bind mount, and explicit CPU/memory/PID limits. The Agent receives a minimal container environment. No host credentials, host home, shared Git metadata, or runtime socket are mounted.

The trusted Podman client receives only the environment required for its rootless runtime. Egress proxy and scoped-secret broker are not implemented; profiles requesting either remain ineligible.

## Git metadata isolation

Sandbox-required tasks use independent single-branch clones created with git clone --no-hardlinks --no-local. The clone has no origin remote, uses a non-personal local commit identity, and has hooks disabled. The workspace is mounted read/write, but .git is mounted read-only inside the Agent container; Git index optional writes, system/global Git configuration and terminal prompts are disabled. Agents can inspect history and diffs but cannot modify refs, index, hooks, config or object metadata. The trusted Integrator stages and commits the reviewed working-tree changes after the container exits.

Legacy non-sandboxed runs continue using linked Git Worktrees. Sandbox-required runs persist workspace_mode=independent-clone in the external journal and reject resumes with a mismatched workspace mode. During integration, the trusted Orchestrator imports the approved commit from the clone before cherry-picking it into the stable repository.

## Conformance gate

The backend's host capability probe alone is not sufficient to enable tasks. SandboxManager reports enforcement_ready=false until a root-owned marker exists at /etc/easyproject/podman-rootless-conformance.json. The marker must be a regular non-symlink file, root-owned and not group/world writable; it must match the current conformance-suite SHA-256, Podman version, kernel release, required check set and exact image digest.

Run the manual-only workflow on a dedicated self-hosted Linux runner labelled rootless-podman. See [CONFORMANCE.md](CONFORMANCE.md) for requirements and evidence installation. Changing the launcher, suite, Podman, kernel or image invalidates the marker.

## Verification status

GitHub CI validates Python syntax, policy refusal, independent clone metadata, launcher argv and marker gating. It does not prove kernel enforcement. M4.4 remains incomplete until the dedicated worker workflow passes and its root-owned marker is installed on the target worker.
