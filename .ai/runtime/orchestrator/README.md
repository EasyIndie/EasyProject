# Local task orchestrator

`scripts/agent-orchestrate.py` adds a small, serial DAG scheduler on top of the
Task/Handoff Envelope and `scripts/agent-run.py`. It is deliberately local and
single-process: no service, database, parallel workers, GitHub mutations, or
credential management.

## Plan format

Create a JSON plan with a unique task ID per node. Each task points to an existing
Task Envelope file; dependencies refer to task IDs in the same plan.

```json
{
  "protocol_version": "1.0",
  "tasks": [
    {
      "task_id": "docs",
      "task_file": ".ai/runtime/examples/task.json",
      "harness": "codex",
      "depends_on": [],
      "max_attempts": 2
    },
    {
      "task_id": "tests",
      "task_file": ".ai/runtime/examples/task.json",
      "harness": "claude-code",
      "depends_on": ["docs"],
      "max_attempts": 1
    }
  ]
}
```

Supported harnesses are `pi`, `codex`, and `claude-code`. Retry count is
bounded to 1–5 attempts. The scheduler validates unknown dependencies, duplicate
IDs, self-dependencies, and cycles before executing anything.

## Run and resume

```bash
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --dry-run --worktrees
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --resume --worktrees
# From another terminal, request cancellation of a running task:
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --resume --worktrees --cancel docs
```

The default journal is `.agent-runs/orchestrator/orchestrator-state.json`. Add `--worktrees` to run each task in its own detached worktree. Worktrees are created beside the repository under `.<repo-name>-agent-worktrees/` so they cannot be nested inside the primary checkout.
Use a different `--runs-dir` for independent runs. The journal is atomically
replaced after each state transition. Do not edit it while a run is active.

Only one agent process is invoked per command. A successful adapter exit produces
`awaiting_review`, not `completed`. With `--worktrees`, the orchestrator captures
a review bundle under the run directory:

- `review-evidence.json`: base commit, changed-file manifest, diff summary,
  whitespace-check result, and a workspace fingerprint.
- `review.diff`: tracked and untracked textual/binary Git diff output.
- The acceptance section remains `pending_human_review`; natural-language
  criteria are never auto-certified by the collector.

Inspect the handoff, raw logs, review bundle, and Task Envelope acceptance
criteria before approving:

```bash
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --resume --worktrees --approve docs
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --resume --worktrees --integrate docs
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --resume --worktrees
```

For worktree tasks, approval rechecks the workspace fingerprint against the
captured evidence and rejects approval if any file changed after review or
`git diff --check` failed. A successful approval moves the task to
`approved`, but does not yet unlock dependents. The separate `--integrate`
step requires a clean target checkout on a named branch whose history contains
the task's recorded base commit. It stages the complete reviewed worktree tree,
normalizes any agent-created commits back to the recorded base, checks the full
staged file manifest, creates one local integration commit, and cherry-picks
that commit onto the current target branch. This preserves earlier agent commits
as part of the reviewed result rather than cherry-picking only the last commit. Only after that
local cherry-pick succeeds does the task become `completed` and unlock its
dependents. The next dependent worktree is therefore based on the newly
integrated target-branch HEAD.

If the target branch has diverged without containing the recorded base commit,
integration stops; do not force it. If cherry-pick conflicts, the orchestrator
records `integration_conflict` and leaves Git's conflict state intact. Resolve
the conflict manually, stage the resolution, run `git cherry-pick --continue`,
then rerun the same `--integrate` command to finalize the journal. Do not start
another task while a cherry-pick is in progress. If you abort the cherry-pick,
preserve the journal and reconcile the task deliberately before retrying.

The integration commit remains local. This milestone does not push, create a
PR, merge remotely, deploy, or publish. The evidence check is an integrity
guard, not proof that product acceptance criteria passed.

Failed process executions are retried up to `max_attempts`; exhausted failures
block dependent tasks. A crash while a task
is marked `running` requires human inspection before manually reconciling the
journal—automatic replay could duplicate partial edits.

## Cancellation and timeouts

Use `--cancel TASK_ID` from a second terminal while the orchestrator is
running. It writes an attempt-scoped request marker; the active runner polls
that marker and terminates the harness process group. The same mechanism is
checked while allowlisted acceptance checks are running. Cancellation returns
exit code 130, records the task as `cancelled`, and does not automatically
retry it; dependent tasks become `blocked`. The cancel command reports that a
request was written, not that termination has already completed—check the run
journal for the final status. Supply the same `--worktrees` mode and
`--runs-dir` as the original run.

Task `timeout_minutes` controls the harness runtime. On timeout, the runner
terminates the process group (POSIX) or attempts process-tree termination on
Windows, saves captured stdout/stderr, and returns exit code 124. The
orchestrator marks the task retryable while attempts remain; exhausted tasks
become `failed` and block dependents. Each acceptance check has its own
15-minute timeout and uses the same cancellation marker. Worktrees and logs are
retained after cancellation or timeout for inspection; cleanup is deliberately
manual so partial work is not silently discarded.

If the orchestrator itself crashes or the machine is powered off, a journal
left in `running` is not proof that the child process is still alive. Inspect
the process list and worktree before restarting or reconciling the journal;
never blindly replay a possibly partially executed task.

## Acceptance checks

Task Envelopes may optionally include `acceptance_checks`. These are IDs, not
shell strings or arbitrary argument arrays. The schema accepts only this fixed
allowlist:

| ID | Executed command |
| --- | --- |
| `python-unittest` | Current Python interpreter, unittest discovery in `tests/` |
| `pytest` | `pytest` |
| `swift-test` | `swift test` |
| `cargo-test` | `cargo test` |
| `npm-test` | `npm test` |
| `go-test` | `go test ./...` |
| `repo-validation` | `bash scripts/validate-repo.sh` |

The orchestrator invokes these as argument arrays with `shell=False`; the task
cannot provide a custom executable, shell fragment, or arguments. Each check
has a 15-minute timeout. stdout/stderr are saved under
`<runs-dir>/<task-id>/checks/attempt-N/` and summarized in the review evidence
and run journal. A missing executable, timeout, or non-zero exit fails the
check set and prevents approval; the task becomes retryable while attempts
remain. When no checks are configured, the evidence explicitly says
`not_configured` and still requires human review.

These are allowlisted launch commands, not a sandbox: project test code and
build scripts execute with the local user's permissions. Configure checks only
for repositories whose code and test scripts you trust. Passing automated
checks does not certify natural-language acceptance criteria.

## Isolated worktrees

```bash
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --dry-run --worktrees
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --worktrees
```

Each task gets a detached worktree created from the repository's current HEAD.
Retries reuse that task's worktree; resume validates that the recorded directory
still belongs to this repository. The --worktrees flag must be repeated on every
resume invocation; the journal rejects a mode mismatch. The runner receives an explicit `--cwd` and
executes the selected harness inside that worktree while loading task/schema
contracts from the template checkout.

Worktree isolation is filesystem isolation, not a security sandbox. Agent CLI
permissions still apply. Worktrees are intentionally retained after review and
integration so the original evidence and task branch remain available for audit.
The explicit `--integrate` action creates a local commit and cherry-picks it; it
does not rebase, push, create a PR, merge remotely, or remove worktrees.

DAG dependencies gate on the `completed` state. For worktree tasks that
means both human approval and successful local integration. The next dependent
task is created from the repository HEAD after the predecessor's integration,
so it can build on the approved predecessor commit.

## Safety and current limitations

- Uses the existing adapter's permission checks; this is not an OS sandbox.
- Network, secret access, and external side effects remain rejected by the adapter.
- No automatic Git commit, push, PR creation, merge, deployment, or publication.
- Serial execution only. Without `--worktrees`, tasks share the primary working tree; with it, each task receives a separate detached worktree.
- Human approval is required before a worktree task can be integrated; approval and integration are separate journal transitions.
- Non-worktree tasks retain the simpler approval-to-completed transition.
- Integration is local-only: no push, remote PR, merge, deployment, or publication.
- The journal is a local recovery aid, not a distributed lock or tamper-proof audit log.
- Concurrent scheduling and richer event-stream parsing are deferred to later milestones. Cancellation is cooperative through an attempt-scoped marker and requires the active runner to remain alive to observe it.
