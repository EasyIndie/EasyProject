# Self-evolution milestone

## Objective

Make EasyProject capable of improving itself in an isolated candidate environment while using the candidate runtime to execute and validate a real Agent task.

## M3.5 acceptance criteria

- Stable checkout must be clean before a candidate is created.
- Candidate branch and worktree are created from an explicit stable base commit.
- Candidate runtime, not stable runtime, executes the evolution task.
- Coding Agent edits only a nested task worktree.
- Task permissions deny network, secrets, and external side effects.
- Automated acceptance checks are selected only from the existing fixed allowlist.
- Handoff, raw logs, review evidence, and journal are retained.
- Human approval and local integration remain separate steps.
- No automatic push, PR creation, remote merge, branch-protection change, deployment, or publication.
- Tests cover run-ID validation, least-privilege task construction, allowlist enforcement, and plan generation.

## Implemented in this milestone

- `scripts/evolution.py` creates a candidate branch/worktree and starts the candidate's own orchestrator.
- Candidate task and plan are stored under ignored `.agent-runs/evolution/<id>/`.
- `run status|resume|approve|integrate` controls the candidate's existing journal and approval flow.
- `tests/test_evolution.py` covers the task contract and generated plan.

## Deferred

- A real authenticated Agent E2E run on a developer machine.
- Benchmark comparison between stable and candidate runtime.
- Container/VM sandbox enforcement.
- Multi-agent parallel evolution.
- Automated GitHub PR creation and CI polling.
- Automatic release or promotion.

These are separate capabilities and must not be inferred from the local self-evolution runner.
