# Agent runtime contract

This directory defines a harness-neutral interchange contract. It is a protocol boundary, not an agent runner: it does not launch tools, store credentials, select models, or promise feature parity between harnesses.

## Design goals

- Keep task intent and acceptance criteria independent of Pi, Codex, and Claude Code.
- Preserve each harness's existing authentication and model configuration; never copy credentials into task files.
- Make permissions explicit and default to least privilege.
- Require evidence-backed handoffs so orchestration can distinguish completed work from claims.
- Allow a human or external orchestrator to run one or more harnesses without changing the task payload.

## Self-evolution

See [the isolated self-evolution runtime guide](evolution/README.md) for running EasyProject in a stable/candidate worktree arrangement and validating changes with the candidate runtime itself.

## Protocol files

- `schemas/task.schema.json`: task request envelope, including optional fixed-ID `acceptance_checks`.
- `schemas/handoff.schema.json`: agent result and handoff envelope.
- `examples/task.json`: minimal valid task example.
- `adapters/README.md`: mapping guidance for supported harnesses.

## Lifecycle

1. Orchestrator creates a task envelope with a stable ID and acceptance criteria.
2. Adapter maps the envelope into the target harness's native invocation. It must not silently widen permissions.
3. Agent reads repository instructions and performs the bounded task.
4. Adapter/orchestrator captures a handoff with changed files, verification evidence, risks, and status.
5. Orchestrator runs only the task's schema-allowlisted acceptance check IDs, captures their logs, and keeps natural-language criteria pending human review.
6. Orchestrator decides whether to retry, delegate, request approval, or finish based on process outcome, automated checks, and human approval.

## Permission model

`permissions` describes the maximum task-level capability, not a credential grant. The runtime must enforce these values separately. Missing or unknown permissions must be treated as denied. Human approval is required for destructive operations, external publication/deployment, secret access, repository security changes, and merges unless an explicit policy grants them.

## Status semantics

- `completed`: all acceptance criteria are met and evidence is supplied.
- `partial`: useful work is done, but one or more criteria remain unmet.
- `blocked`: the task cannot proceed safely or lacks required inputs.
- `failed`: execution was attempted and did not produce an acceptable result.

Do not use `completed` when checks were skipped or when the result relies on unverified assumptions.
