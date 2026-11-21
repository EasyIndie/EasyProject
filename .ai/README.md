# AI Workspace

This directory contains shared project context, rules, role contracts, workflows, prompts, templates, and durable decisions.

## Session entry

1. Read the repository root [AGENTS.md](../AGENTS.md).
2. Read the relevant files under `context/`; do not assume placeholder context is complete.
3. Read only the rules relevant to the task under `rules/`.
4. Choose the smallest suitable workflow under `workflows/`.
5. Use role contracts under `agents/` when work is delegated or handed off.

## Structure

| Directory | Purpose |
|---|---|
| `context/` | Project purpose, users, architecture, constraints, and stack |
| `rules/` | Shared engineering, Git, documentation, and safety rules |
| `agents/` | Tool-agnostic role contracts and handoff expectations |
| `workflows/` | Quick Change, Feature Development, and Major Change |
| `prompts/` | Reusable task prompts |
| `templates/` | Lightweight specs, ADRs, plans, and reports |
| `memory/` | Durable decisions and project facts worth retaining |

## Principles

- Context before implementation; verify that context is current.
- Rules apply across agents and tools.
- Use the smallest workflow that matches risk.
- Agent role files define responsibilities, not an assumed orchestration runtime.
- Keep durable project knowledge; avoid duplicating transient chat history.
- Do not create empty documentation or folders just to satisfy a convention.

See [agent contracts](agents/README.md) and [workflow selection](workflows/README.md).
