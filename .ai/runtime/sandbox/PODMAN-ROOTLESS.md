# Linux Rootless Podman Backend (M4.4.1–M4.4.3)

This backend is intentionally narrow: Linux, rootless Podman, cgroup v2, systemd user-service delegation, and delegated cpu/memory/pids controllers. It refuses rootful Podman, cgroup v1, missing subordinate UID/GID mappings, missing resource controllers, mutable image tags, and shared Git worktree metadata.

## Runtime image

Every profile must set runtime.backend=linux-rootless-oci and an immutable OCI reference of the form registry/name@sha256:<64 lowercase hex>. The image must already exist in rootless Podman's local image store; launch uses --pull=never. The example uses a syntactically valid placeholder digest only; it is not a published or verified image.

## Launch boundary

The launcher applies rootless user namespaces, private PID/network/IPC/cgroup namespaces, network=none, read-only container root, dropped capabilities, no-new-privileges, private tmpfs mounts, one task-workspace bind mount, and explicit CPU/memory/PID limits. The Agent receives a minimal container environment. No host credentials, host home, shared Git metadata, or runtime socket are mounted.

The trusted Podman client receives only the environment required for its rootless runtime. Egress proxy and scoped-secret broker are not implemented; profiles requesting either remain ineligible.

## Git metadata isolation

When Orchestrator runs with both --require-sandbox and --worktrees, it creates a full independent clone with git clone --no-hardlinks --no-local, restricted to the current source branch. It removes the clone's origin remote, assigns a non-personal local commit identity, and verifies that .git is a private directory without commondir or object alternates. The container mounts the entire independent task clone read/write, including its private .git directory, so the Agent can create the commit consumed by the existing Integrator flow. This is safe only because the clone has its own object database and refs, no origin remote, and no shared common-dir or object alternates; it is not the stable repository. The container cannot access the stable checkout. Git global/system configuration and terminal prompts are disabled, and hooks are configured off when the clone is created. Any task-local Git writes remain confined to the disposable sandbox.

Legacy non-sandboxed task runs continue using linked Git Worktrees. Sandbox-required runs persist workspace_mode=independent-clone in the external journal and reject resumes with a mismatched workspace mode. During integration, the trusted Orchestrator fetches the approved commit from the clone into the stable repository before cherry-picking it. The clone is never allowed to write the stable repository's refs or object store.

## Verification status

CI unit tests cover clone metadata independence, workspace reuse, commit import, launcher argv construction, image pinning, and environment shaping. They do not prove kernel enforcement. M4.4.4 still requires a dedicated Linux worker conformance suite against the actual Podman, cgroup and systemd configuration.
