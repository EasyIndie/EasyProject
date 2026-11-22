# Self-evolution runtime

For a fresh local clone, Agent session startup, canonical-template detection, harness routing, isolated iteration, and the human review/PR handoff, start with the [local template maintenance and self-evolution playbook](AGENT-PLAYBOOK.md). The playbook is the Agent-facing entry point; this document remains the detailed runtime command reference.

EasyProject self-evolution uses two nested workspaces with a trusted control plane:

1. The **stable checkout** owns the trusted Evolution entry point, Orchestrator, and Agent Runner code.
2. The control plane operates on a candidate Git worktree and creates a second task worktree for the coding Agent.

The candidate is mutable and must never supply the Orchestrator or Runner executable code used to control itself. The stable checkout is never the Agent's write workspace. The candidate branch is not merged or pushed automatically. **All mutable run data is stored outside both Git worktrees**, so task envelopes, plans, journals, logs, and evidence cannot pollute the template or candidate source tree.

## Discover, approve, and execute a candidate

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

Then explicitly submit the approved artifact to Evolution. The run ID must match
the candidate Task Envelope ID:

```bash
python3 scripts/evolution.py start \
  --id DISC-0123456789ab \
  --approved-task ../approved-task.json \
  --harness codex
```

Evolution revalidates the artifact's approval mode, repository base SHA, tracked
source path, file hash, marker location, task ID, permissions, and schema. The
Agent runs in the candidate's nested worktree. Network, secret access, and
external side effects remain denied. This command starts a real Agent, so run
it only after inspecting the task and confirming the local CLI configuration.

The promotion artifact uses format version 1.1 and includes a SHA-256 digest
covering its approval fields, evidence, and complete Task Envelope. Evolution
rejects artifacts whose covered content has changed. This detects accidental
post-approval edits; it is **not a digital signature or identity proof**. A
person able to rewrite the artifact and recompute its digest can still create
a different artifact, so review and protect the file as an approval record.
Older version 1.0 artifacts must be regenerated before execution.

See [the discovery and approval contract](../discovery/README.md) for full semantics.

## Start a generic self-evolution task

For tasks not originating from discovery, use an explicit goal:

```bash
python3 scripts/evolution.py start \
  --id m35-first-run \
  --harness codex \
  --goal "Implement the next approved EasyProject self-evolution capability" \
  --check python-unittest
```

Requirements:

- A clean EasyProject checkout on a named branch.
- Python with the repository's `jsonschema` dependency installed.
- A configured and authenticated `codex`, `claude`, or `pi` CLI on `PATH`.
- The selected Agent CLI must be permitted to write to its isolated workspace by its own local permission configuration.

Pi has no OS-level sandbox. Pi Evolution write tasks are rejected by default. Supply `--allow-unsandboxed-pi-write` explicitly to `evolution.py start` only after accepting host-access risk. Evolution records this human opt-in in its external runtime manifest and forwards it as an Orchestrator CLI control-plane flag; an editable Task Envelope cannot grant the permission. The override does not create a sandbox and a Worktree does not restrict host access. Prefer Codex (`workspace-write` sandbox) until the whole-process task sandbox is implemented.

First run the non-mutating prerequisite check. It verifies the Git checkout, clean working tree, Python dependency, and CLI executable/version. It does not inspect or print credentials and does not prove that the CLI is authenticated:

```bash
python3 scripts/evolution.py doctor --harness codex
python3 scripts/evolution.py doctor --harness pi
```

The external runtime directory also contains `manifest.json`, which records the stable base SHA, branch, CLI version, Python/jsonschema versions, goal, task source, and configured checks. It never records credential values.

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
    ├── runtime/       # manifest and plan
    │   └── orchestrator/  # task envelope, journal, logs, checks, evidence
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
