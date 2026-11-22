# Linux Rootless Podman Conformance

## Purpose

The launcher and capability probe are not proof of kernel enforcement. This suite runs real containers and checks workspace boundaries, host-path isolation, network denial, private PID namespace, effective cgroup limits, read-only Git metadata and descendant cleanup. Until the suite has passed on the actual target Linux worker and its root-owned evidence marker is installed, SandboxManager must report enforcement_ready=false and refuse sandbox-required tasks.

## Runner requirements

- Dedicated Linux self-hosted GitHub Actions runner with labels self-hosted, linux, x64 and rootless-podman.
- Rootless Podman with cgroup v2, systemd user-service delegation and cpu/memory/pids controllers.
- An OCI image already loaded into that user's rootless Podman store and pinned by digest.
- The image must contain Python 3, Git and sleep. Do not give the runner or image any production credentials.
- The runner must have a writable home and XDG_RUNTIME_DIR.

## Run manually

On the dedicated worker, preload the trusted test image by digest, then run:

```bash
python3 scripts/sandbox_conformance.py --image registry.example/agent@sha256:<64-hex-digest> --evidence sandbox-conformance-evidence.json
```

Or dispatch the Linux sandbox conformance workflow from the trusted main branch and provide the same preloaded image reference. The workflow is manual-only and does not run untrusted pull-request code on the self-hosted runner.

## Evidence installation

The suite writes a JSON evidence candidate containing the exact image digest, conformance-suite SHA-256, Podman version, kernel release, timestamp and passed check IDs. Review the run and then install the file as root:

```bash
sudo install -D -o root -g root -m 0644 sandbox-conformance-evidence.json /etc/easyproject/podman-rootless-conformance.json
python3 scripts/sandbox_runtime.py doctor
```

The backend accepts the marker only when it is a regular non-symlink file, root-owned, not group/world writable, and matches the current suite hash, Podman version, kernel release and required check set. A profile's runtime.image must exactly match the image digest recorded by the marker. Updating the launcher, conformance suite, Podman or kernel invalidates the marker and requires a fresh run.

## What a pass does not mean

This verifies the tested Rootless Podman configuration and exact image on one worker. It does not implement credential brokering, controlled network egress, gVisor/Kata/Firecracker isolation or hosted-model authentication. Those remain separate M4.5/M4.6 work. Do not copy the marker to another machine or use it with a different image.
