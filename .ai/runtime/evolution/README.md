# Self-evolution runtime

EasyProject self-evolution uses two nested isolation boundaries:

1. The **stable checkout** creates and controls a candidate Git worktree.
2. The candidate's own **Evolution runtime** runs the task orchestrator, which creates a second worktree for the coding Agent.

The stable checkout is never the Agent's write workspace. The candidate branch is not merged or pushed automatically. **All mutable run data is stored outside both Git worktrees**, so task envelopes, plans, journals, logs, and evidence cannot pollute the template or candidate source tree.

## Start a real evolution run

Requirements:

- A clean EasyProject checkout on a named branch.
- Python with the repository's `jsonschema` dependency installed.
- A configured and authenticated `codex` or `claude` CLI on `PATH`.
- The selected Agent CLI must be permitted to write to its isolated workspace by its own local permission configuration.

From the stable checkout:

```bash
python3 scripts/evolution.py start \
  --id m35-first-run \
  --harness codex \
  --goal "Implement the next approved EasyProject self-evolution capability" \
  --check python-unittest
```

The command creates this sibling directory structure (not inside the repository):

```text
../.EasyProject-evolution/
└── m35-first-run/
    ├── candidate/     # candidate Git worktree
    ├── runtime/       # task, plan, journal, logs, evidence
    └── .candidate-agent-worktrees/  # nested Agent worktrees (managed by orchestrator)
```

The candidate branch is named `evolution/<id>` and is based on the stable checkout's current HEAD. The candidate's own `scripts/agent-orchestrate.py` and `scripts/agent-run.py` execute the task. The Agent receives repository-write permission only inside its nested task worktree. Network, secret access, and external side effects are denied by the Task Envelope.

## Review and integrate inside the candidate

After the real Agent run reaches `awaiting_review`, inspect the handoff, diff, logs, and evidence in the external `runtime/` directory. Then:

```bash
python3 scripts/evolution.py run --id m35-first-run status
python3 scripts/evolution.py run --id m35-first-run approve
python3 scripts/evolution.py run --id m35-first-run integrate
```

To resume a retryable task, use `resume`. Approval and integration are separate explicit actions. Integration creates a local commit on the candidate branch only.

After integration, run the full repository validation in the candidate checkout:

```bash
cd ../.EasyProject-evolution/m35-first-run/candidate
python3 -m unittest discover --start-directory tests --pattern 'test_*.py'
bash scripts/validate-repo.sh
git status --short
git log -1 --oneline
```

Review the complete candidate diff against the stable base. Push the candidate branch and create a PR only through a separately reviewed GitHub workflow. This tool never pushes, creates PRs, changes branch protection, merges, deploys, or publishes.

## Stable / candidate lifecycle

- Stable checkout: creates the candidate, remains unchanged, and retains the known-good runtime.
- Candidate checkout: runs the candidate version of the runtime.
- Agent task worktree: receives code edits and automated acceptance checks.
- External runtime directory: stores mutable task inputs, journal, logs, and evidence.
- External task-worktree directory: stores nested Agent worktrees, adjacent to the candidate and runtime directories.
- Human gate: review evidence, approve, then integrate into the candidate branch.
- Promotion: human review and normal CI/PR policy are required before candidate code reaches `main`.

The candidate and runtime directories are intentionally retained for inspection. Do not delete them until evidence has been reviewed and any needed artifacts have been preserved.

## Template cleanliness and bootstrap verification

Run `python3 scripts/check-template-cleanliness.py` to ensure generated Evolution runtime directories have not been committed. The repository validation workflow runs this check in a fresh CI checkout. Bootstrap dry-run and idempotency are covered by the bootstrap end-to-end tests.

## Limitations

- This is a local runner, not a hosted service or a security sandbox.
- Git worktrees provide filesystem separation, not OS-level isolation.
- Agent CLIs and test/build scripts still run with the local user's OS permissions. Use a disposable VM/container with restricted credentials and network for stronger isolation.
- Pi's current adapter is read-only and therefore is not offered as the self-evolution coding harness. It can still be used for planning or review outside this write path.
- A successful CLI exit and passing automated checks produce `awaiting_review`, not automatic approval.
- CI can test the runner's contracts, but a real Agent E2E run requires the user's locally installed and authenticated CLI. Never report a simulated test as a real Agent run.
