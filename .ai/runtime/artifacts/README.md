# Immutable Artifact Broker (M4.3)

## Purpose and trust boundary

The Artifact Broker is the target trusted control-plane utility for file exchange between Agent tasks, reviewers and the integrator. The standalone CLI and immutable storage contract are implemented. Orchestrator integration now exports a review artifact only for sandbox-required tasks after the Runner and sandboxed acceptance checks complete; approval and integration re-verify the artifact and bind it to the current review fingerprint. Agents must not share writable directories.

The broker must run after the producing Agent and its descendants have stopped. The sandbox backend contract now requires termination of every task descendant before the launcher reports completion. Exporting a workspace while any Agent or check process is still writing creates a time-of-check/time-of-use race and does not produce a reliable snapshot. The broker validates source paths and file metadata, but a frozen source workspace is an operational precondition.

## Artifact format

Each artifact is stored in a content-addressed directory:

```text
<artifact-store>/
  sha256-<manifest-sha256>/
    artifact.json
    <declared relative files...>
```

The manifest records protocol version, artifact ID, task ID, kind, creation time, source Git revision, per-file SHA-256 and byte count, and total bytes. The artifact ID is the SHA-256 of canonical manifest JSON without the ID and creation-time fields, so identical task/kind/revision/file content exports idempotently.

Files are copied, never hard-linked. The store and source workspace must be disjoint. Files and directories are made read-only after export. The receiver must run `verify` before use; read-only permissions are defense in depth, not proof against the store owner.

## Validation rules

- Only normalized relative POSIX paths are accepted; absolute paths, drive paths, backslashes, empty components, `.` and `..` are rejected.
- Symlinks, hard links, devices, FIFOs, sockets and other special files are rejected.
- Sensitive path names such as `.env*`, `.ssh`, `.aws`, `.kube`, `.npmrc`, credentials, private keys and keystores are never exportable.
- Maximum 128 files, 10 MiB per file, 50 MiB total.
- Duplicate paths, path traversal, symlink parents, changed files and undeclared files are rejected.
- Verification revalidates the manifest, canonical artifact ID, each file size/hash, and the exact file set.
- Materialization creates a new, non-existing, read-only reviewer snapshot. It never applies files to the stable checkout.

Legacy unsandboxed Orchestrator runs do not auto-export artifacts. Sandbox-required runs require `--require-sandbox --worktrees`; if the Runner handoff does not say `sandbox_status: enforced`, or a check cannot be sandboxed, the task cannot be approved or integrated.

Sensitive-name filtering is a conservative guard, not a complete secret scanner. Do not put credentials in task workspaces. A future credential broker must keep raw secrets outside the Agent and artifact planes.

## CLI

Export a declared set of files after the task has stopped:

```bash
python3 scripts/artifact_broker.py export \
  --workspace .agent-runs/workspaces/task-01 \
  --store .agent-runs/artifacts \
  --task-id task-01 \
  --kind test-report \
  --source-revision 0123456789abcdef \
  --path reports/test-report.json \
  --path build/verification.txt
```

Verify before a reviewer consumes the artifact:

```bash
python3 scripts/artifact_broker.py verify \
  --artifact-dir .agent-runs/artifacts/sha256-<digest>
```

Create a read-only reviewer snapshot (including the provenance manifest):

```bash
python3 scripts/artifact_broker.py materialize \
  --artifact-dir .agent-runs/artifacts/sha256-<digest> \
  --destination .agent-runs/reviewer/task-01
```

## Non-goals

- No automatic patch application, commit, merge, push or deployment.
- No direct writable workspace sharing.
- No claim that content hashing proves source authenticity; the trusted control plane must bind the artifact to a task and expected base revision.
- No claim that the broker prevents an Agent from embedding a secret in ordinary source text; sensitive path checks are not a DLP system.
