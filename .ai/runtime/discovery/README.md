# Evidence-based task discovery

`scripts/agent-discover.py` scans Git-tracked UTF-8 text files for explicit
`TODO`, `FIXME`, and `HACK` markers. It emits deterministic review candidates
with file path, line number, and source-file SHA-256 evidence.

```bash
python3 scripts/agent-discover.py
python3 scripts/agent-discover.py --max-candidates 25 --output ../easyproject-discovery.json
```

## Safety and semantics

- This is a narrow signal collector, not a bug detector or autonomous planner.
- A marker is not proof of a defect; every candidate must be reviewed.
- Only Git-tracked files are scanned. Binary, non-UTF-8, and files larger than
  1 MiB are skipped. The discovery script and its own tests are excluded.
- Raw source lines are not copied into the report; evidence contains path, line,
  marker type, and file hash.
- The output wraps valid Task Envelopes, but repository write, network, secret,
  and external-side-effect permissions are all false.
- The tool does not execute Agents, alter files, create Issues, or invoke GitHub.
- Candidates are not queued for execution. A human must validate the evidence,
  revise the task scope and permissions if needed, and explicitly approve a
  separate execution workflow.

This first discovery milestone intentionally favors precision and traceable
evidence over broad heuristic coverage. Future rules should be added only with
fixtures that demonstrate useful signal and bounded false positives.
