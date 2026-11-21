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
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --resume
```

The default journal is `.agent-runs/orchestrator/orchestrator-state.json`. Add `--worktrees` to run each task in its own detached worktree. Worktrees are created beside the repository under `.<repo-name>-agent-worktrees/` so they cannot be nested inside the primary checkout.
Use a different `--runs-dir` for independent runs. The journal is atomically
replaced after each state transition. Do not edit it while a run is active.

Only one agent process is invoked per command. A successful adapter exit produces
`awaiting_review`, not `completed`; inspect the handoff, raw logs, working-tree
diff, and acceptance criteria before approving:

```bash
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --resume --approve docs
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --resume
```

Approval unlocks dependent tasks. Failed process executions are retried up to
`max_attempts`; exhausted failures block dependent tasks. A crash while a task
is marked `running` requires human inspection before manually reconciling the
journal—automatic replay could duplicate partial edits.

## Isolated worktrees

```bash
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --dry-run --worktrees
python3 scripts/agent-orchestrate.py --plan .ai/runtime/examples/plan.json --worktrees
```

Each task gets a detached worktree created from the repository's current HEAD.
Retries reuse that task's worktree; resume validates that the recorded directory
still belongs to this repository. The runner receives an explicit `--cwd` and
executes the selected harness inside that worktree while loading task/schema
contracts from the template checkout.

Worktree isolation is filesystem isolation, not a security sandbox. Agent CLI
permissions still apply. Worktrees are intentionally retained after review so
uncommitted changes are not lost. Inspect and integrate changes manually; this
milestone does not commit, cherry-pick, rebase, push, or remove worktrees.

DAG dependencies currently gate execution order only. A dependent task starts
from the repository HEAD, not from uncommitted changes in its predecessor's
worktree. Integrate approved predecessor changes into the base branch before
starting dependent tasks that need those changes.

## Safety and current limitations

- Uses the existing adapter's permission checks; this is not an OS sandbox.
- Network, secret access, and external side effects remain rejected by the adapter.
- No automatic Git commit, push, PR creation, merge, deployment, or publication.
- Serial execution only. Without `--worktrees`, tasks share the primary working tree; with it, each task receives a separate detached worktree.
- Human approval is the only transition from `awaiting_review` to `completed`.
- The journal is a local recovery aid, not a distributed lock or tamper-proof audit log.
- Concurrent scheduling, cancellation, automatic change integration, and richer event-stream parsing are deferred to later milestones.
