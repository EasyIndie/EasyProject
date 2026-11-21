# Agent role contracts

Role files define responsibilities and handoffs; they do not imply that a specific multi-agent runtime is installed. A human or orchestrator may assign these roles to separate agents, or one agent may perform multiple roles sequentially.

Every role follows the canonical [AGENTS.md](../../AGENTS.md) contract. Tool-specific agent manifests belong in the relevant harness directory and should reference—not fork—these role definitions.

## Available roles
- [Planner](planner.md): clarify outcomes, constraints, and acceptance.
- [Architect](architect.md): evaluate boundaries, interfaces, and trade-offs.
- [Developer](developer.md): implement a bounded change.
- [Reviewer](reviewer.md): independently inspect correctness and risk.
- [QA](qa.md): design and execute verification.
- [DevOps](devops.md): CI, delivery, and operational safety.

## Handoff format
Each handoff includes task/issue, inputs inspected, decisions, files changed, checks and results, unresolved risks, and the next role/action. A role must not claim work or verification performed by another role unless it has inspected the evidence.
