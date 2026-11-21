# Delivery workflows

Choose a workflow based on risk and scope—not habit. A workflow is a decision aid, not a ceremony.

| Workflow | Use when | Minimum artifacts |
|---|---|---|
| [Quick Change](quick-change.md) | Small, isolated, low-risk edits | Change summary and relevant check |
| [Feature Development](feature-development.md) | User-visible behavior, APIs, or multi-component work | Brief/spec, implementation plan, tests, review |
| [Major Change](major-change.md) | Architecture, data migration, security, release, or high-impact changes | ADR/design, migration and rollback plan, staged verification |

If unsure, start with the smaller workflow and escalate when evidence reveals higher risk. A PRD is not required for typo fixes, routine documentation, or isolated configuration changes.
