# Documentation rules

Documentation exists to preserve decisions, explain behavior, and make work verifiable—not to maximize file count.

## What must be documented

| Change | Expected documentation |
|---|---|
| Non-trivial user-facing behavior | Spec or acceptance criteria |
| Durable architecture decision | ADR in `architecture/adr/` |
| Public API or data contract | API/schema docs and compatibility notes |
| Operationally significant change | Runbook, deployment, rollback, or monitoring notes |
| New dependency or platform constraint | Update project context and rationale |

## Proportionality

- Trivial typo, formatting, or isolated config changes do not need a PRD.
- A small feature may use a concise task brief and acceptance checklist.
- A major or irreversible change needs a design decision, migration plan, and rollback strategy.
- Do not create a README in every directory by default. Add an index when it helps a new contributor navigate non-obvious content.
- Keep documentation close to the relevant code or domain when that improves discoverability.

## Maintenance

Update documentation when behavior, interfaces, operational procedures, or durable decisions change. Remove stale instructions when replacing a workflow; do not leave conflicting guidance active.
