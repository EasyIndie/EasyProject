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
Promotion does not start an Agent or create a plan; the user must separately
review the resulting JSON and start an Evolution run.

Before promotion, the tool verifies the discovery report's repository and base
SHA, confirms the source is still Git-tracked and unchanged, and checks that
the marker remains at the recorded line. Stale evidence is rejected and must
be regenerated. The task is validated against the repository Task Envelope
schema before output.

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
- The approval command never launches Agents, modifies source files, creates
  Issues, or invokes GitHub.
- Candidates are not queued for execution. A human must validate the evidence,
  write the real task scope, and explicitly enable repository writes if needed.

This first discovery milestone intentionally favors precision and traceable
evidence over broad heuristic coverage. Future rules should be added only with
fixtures that demonstrate useful signal and bounded false positives.
