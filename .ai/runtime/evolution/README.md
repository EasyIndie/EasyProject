# Self-evolution runtime

EasyProject self-evolution uses two nested isolation boundaries:

1. The **stable checkout** creates and controls a candidate Git worktree.
2. The candidate's own **Evolution runtime** runs the task orchestrator, which creates a second worktree for the coding Agent.

The stable checkout is never the Agent's write workspace. The candidate branch is not merged or pushed automatically. **All mutable run data is stored outside both Git worktrees**, so task envelopes, plans, journals, logs, and evidence cannot pollute the template or candidate source tree.

## Discover and approve a candidate

Run the read-only discovery scan:

```bash
python3 scripts/agent-discover.py --output ../easyproject-discovery.json
```

Review the evidence and write a precise objective and acceptance criteria. Promote only a candidate that has a clear, bounded purpose:

```bash
python3 scripts/agent-task-approve.py \
  --report ../easyproject-discovery.json \
  --candidate-id DISC-0123456789ab \
  --objective "Implement the reviewed maintenance improvement" \
  --acceptance-criterion "The reported issue is resolved" \
  --acceptance-criterion "Relevant regression tests pass" \
  --approval-note "Reviewed the source evidence and approved this task" \
  --harness codex \
  --check python-unittest \
  --approve-write \
  --output ../approved-task.json
```

The approval tool revalidates the repository base SHA, tracked source path, file hash,
and marker location. It validates the promoted Task Envelope against the schema.
Without `--approve-write`, the task stays read-only; with it, only repository-write
permission is enabled. Network, secret access, and external side effects remain denied.
The tool does not launch an Agent. Inspect the generated task before separately
starting an Evolution run.

See [the discovery and approval contract](../discovery/README.md) for full semantics.

## Start a real evolution run

Requirements:

- A clean EasyProject checkout on a named branch.
- Python with the repository's `jsonschema` dependency installed.
- A configured and authenticated `codex` or `claude` CLI on `PATH`.
- The selected Agent CLI must be permitted to write to its isolated workspace by its own local permission configuration.

First run the non-mutating prerequisite check. It verifies the Git checkout, clean working tree, Python dependency, and CLI executable/version. It does not inspect or print credentials and does not prove that the CLI is authenticated:

```bash
python3 scripts/evolution.py doctor --harness codex
```

Then start a run:

```bash
python3 scripts/evolution.py start \
  --id m35-first-run \
  --harness codex \
  --goal "Implement the next approved EasyProject self-evolution capability" \
  --check python-unittest
```

The external runtime directory also contains `manifest.json`, which records the stable base SHA, branch, CLI version, Python/jsonschema versions, goal, and configured checks. It never records credential values.

Print a concise report from the manifest and orchestrator journal at any time:

```bash
python3 scripts/evolution.py report --id m35-first-run
```

The report distinguishes a run that has not started from one with recorded execution state. A task in `awaiting_review` is not approved or integrated.

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
