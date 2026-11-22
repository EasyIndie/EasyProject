# Linux Rootless Podman Backend (M4.4.1–M4.4.2)

This backend is intentionally narrow: Linux, rootless Podman, cgroup v2, systemd user-service delegation, and delegated cpu/memory/pids controllers. It refuses rootful Podman, cgroup v1, missing subordinate UID/GID mappings, missing resource controllers, mutable image tags, and shared Git worktree pointer files.

## Runtime image

Every profile must set `runtime.backend=linux-rootless-oci` and an immutable OCI reference of the form `registry/name@sha256:<64 lowercase hex>`. The image must already exist in rootless Podman's local image store; launch uses `--pull=never`. The example uses a syntactically valid placeholder digest only; it is not a published or verified image.

## Launch boundary

The launcher applies rootless user namespaces, private PID/network/IPC/cgroup namespaces, `network=none`, read-only container root, dropped capabilities, no-new-privileges, private tmpfs mounts, one task-workspace bind mount, and explicit CPU/memory/PID limits. The Agent receives a minimal container environment. No host credentials, host home, shared Git metadata, or runtime socket are mounted.

The trusted Podman client receives only the environment required for its rootless runtime. Egress proxy and scoped-secret broker are not implemented; profiles requesting either remain ineligible.

## Git metadata

A worktree whose `.git` is a pointer file is rejected. Use an independent clone with its own `.git` directory, or make the Agent produce patches without Git metadata. Never mount the host shared Git common directory into the container.

## Verification status

Unit tests cover launcher argv construction, image pinning, Git pointer rejection and environment shaping. They do not prove kernel enforcement. M4.4.4 still requires a dedicated Linux worker conformance suite against the actual Podman, cgroup and systemd configuration.
