# Evidence-based task discovery and approval

## Discover candidates

`scripts/agent-discover.py` scans Git-tracked source and configuration files
for explicit `TODO`, `FIXME`, and `HACK` markers. It emits deterministic
review candidates with file path, line number, and source-file SHA-256 evidence.

```bash
python3 scripts/agent-discover.py
python3 scripts/agent-discover.py --max-candidates 25 --output ../easyproject-discovery.json
```

## Promote one reviewed candidate

A candidate is not an executable coding task. First inspect its evidence and
decide what the actual work should be. Then provide a bounded objective,
acceptance criteria, and an approval note:

```bash
python3 scripts/agent-task-approve.py \
  --report ../easyproject-discovery.json \
  --candidate-id DISC-0123456789ab \
  --objective "Resolve the parser TODO and add regression coverage" \
  --acceptance-criterion "The marker is resolved without changing unrelated behavior" \
  --acceptance-criterion "A regression test covers the affected parser behavior" \
  --approval-note "Reviewed source and approved this bounded change" \
  --harness codex \
  --check python-unittest \
  --approve-write \
  --output ../approved-task.json
```

Without `--approve-write`, the promoted Task Envelope remains read-only.
That flag explicitly enables repository writes for the future Agent task, but
network access, secret access, and external side effects remain disabled.

## Start the approved task in Evolution

The approval artifact can be passed directly to Evolution. The run ID must
match the candidate Task Envelope ID:

```bash
python3 scripts/evolution.py start \
  --id DISC-0123456789ab \
  --approved-task ../approved-task.json \
  --harness codex
```

Evolution rechecks the approval mode, base SHA, tracked source path, file hash,
marker location, task ID, permissions, and Task Envelope schema before creating
the candidate worktree. It then starts the normal isolated Agent workflow.

The promotion artifact uses format version 1.1 and includes a SHA-256 digest
covering its approval fields, evidence, and complete Task Envelope. Evolution
rejects artifacts whose covered content has changed. This detects accidental
post-approval edits; it is **not a digital signature or identity proof**. A
person able to rewrite the artifact and recompute its digest can still create
a different artifact, so review and protect the file as an approval record.
Older version 1.0 artifacts must be regenerated before execution.
This is a real Agent execution and should only be run locally after reviewing
the task and confirming the selected CLI configuration. Evolution still does
not push, create remote PRs, merge, deploy, or publish.

## Safety and semantics

- This is a narrow signal collector, not a bug detector or autonomous planner.
- A marker is not proof of a defect; every candidate must be reviewed.
- Only Git-tracked source/configuration files with supported extensions are scanned.
  Documentation examples, binary files, non-UTF-8 files, symlinks, and files
  larger than 1 MiB are skipped. The discovery script and its own tests are excluded.
- Raw source lines are not copied into discovery reports; evidence contains path,
  line, marker type, and file hash.
- Candidate tasks default to no repository-write, network, secret, or
  external-side-effect permissions.
- Promotion never launches Agents, modifies source files, creates Issues, or
  invokes GitHub.
- Execution occurs only after the approved artifact is separately supplied to
  Evolution. Network, secret, and external-side-effect permissions remain denied.

This first discovery milestone intentionally favors precision and traceable
evidence over broad heuristic coverage. Future rules should be added only with
fixtures that demonstrate useful signal and bounded false positives.
