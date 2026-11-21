# Self-evolution milestone

## Objective

Make EasyProject capable of improving itself in an isolated candidate environment while using the candidate runtime to execute and validate a real Agent task, without placing mutable runtime artifacts in the reusable template.

## M3.5 acceptance criteria

- Stable checkout must be clean before a candidate is created.
- Candidate branch and worktree are created from an explicit stable base commit.
- Candidate runtime, not stable runtime, executes the evolution task.
- Coding Agent edits only a nested task worktree.
- Task permissions deny network, secrets, and external side effects.
- Automated acceptance checks are selected only from the existing fixed allowlist.
- All task inputs, journals, logs, evidence, and nested task worktrees live outside the repository.
- Handoff, raw logs, review evidence, and journal are retained.
- Human approval and local integration remain separate steps.
- No automatic push, PR creation, remote merge, branch-protection change, deployment, or publication.

## M3.5.1 template-isolation acceptance

- Candidate source worktree and mutable runtime directory are sibling paths outside the stable checkout.
- The generated plan references an external task file.
- The candidate orchestrator writes its journal, logs, evidence, and nested worktrees under the external runtime directory.
- Tests assert candidate/runtime path separation and external task-plan generation.
- CI rejects tracked generated Evolution runtime directories.
- Bootstrap dry-run and idempotency remain covered by end-to-end tests.

## Implemented

- `scripts/evolution.py` creates a candidate branch/worktree and starts the candidate's own orchestrator.
- Candidate task and plan are stored in the external sibling `runtime/` directory.
- `scripts/check-template-cleanliness.py` prevents generated Evolution runtime directories from being committed.
- Tests cover run-ID validation, least-privilege task construction, allowlist enforcement, path separation, and plan generation.

## Deferred

- A real authenticated Agent E2E run on a developer machine.
- Benchmark comparison between stable and candidate runtime.
- Container/VM sandbox enforcement.
- Multi-agent parallel evolution.
- Automated GitHub PR creation and CI polling.
- Automatic release or promotion.

These are separate capabilities and must not be inferred from the local self-evolution runner.
