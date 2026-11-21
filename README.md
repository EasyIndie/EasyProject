# PROJECT_NAME

> PROJECT_DESCRIPTION

**AI Native Engineering Standard** — a language- and domain-agnostic foundation for human-led, agent-assisted software delivery.

## Quick start

1. Create a repository from this template.
2. Run `bash bootstrap.sh` (or `bash bootstrap.sh --help`).
3. Start an agent with: **"Read AGENTS.md and follow the repository instructions."**
4. Fill in the project context incrementally; do not create documents that do not help a real decision or task.

## Start here

| Entry point | Purpose |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Canonical instructions for all coding agents |
| [`CLAUDE.md`](CLAUDE.md) | Claude Code entry point; delegates to AGENTS.md |
| [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | GitHub Copilot repository instructions |
| [`.ai/README.md`](.ai/README.md) | AI workspace map |
| [`.ai/context/`](.ai/context/) | Project-specific facts and constraints |
| [`.ai/rules/`](.ai/rules/) | Shared engineering and safety rules |
| [`.ai/agents/`](.ai/agents/) | Role contracts and handoff expectations |
| [`.ai/workflows/`](.ai/workflows/) | Task-sized delivery workflows |

## Operating model

The repository has four cooperating layers:

1. **Project context** — what is being built, for whom, and under which constraints.
2. **Agent system** — role contracts, permissions, evidence requirements, and handoffs.
3. **Workflow system** — choose the smallest workflow that safely fits the task.
4. **Project domain** — add domain-specific schemas, validation, simulation, or release rules without polluting the generic template.

### Choose the right workflow

- **Quick change**: typo, docs, isolated config, or a low-risk local fix.
- **Feature development**: user-visible behavior, API changes, or a feature spanning components.
- **Major change**: architecture, data migrations, security boundaries, release strategy, or other high-impact work.

Do not force every change through a heavyweight PRD. Use the smallest amount of planning that makes the change understandable and verifiable.

## Repository structure

```text
.ai/
  agents/       role contracts
  context/      project facts and constraints
  rules/        shared non-negotiable rules
  workflows/    quick / feature / major delivery paths
  prompts/      reusable task prompts
  templates/    lightweight document templates
  memory/       durable project decisions only
.github/
  instructions/ path-specific Copilot instructions
  workflows/    executable CI workflows
architecture/   architecture notes and ADRs when needed
docs/           user and engineering documentation
examples/       illustrative end-to-end examples
scripts/        repository validation and automation
specs/          requirements for non-trivial product changes
tasks/          durable plans and reports; not a second Kanban
apps/           deployable applications (optional)
packages/       reusable packages (optional)
infra/          infrastructure definitions (optional)
tests/          test suites (optional)
```

Directories are optional. Keep the structure that the project actually uses; do not add empty folders or README files solely to satisfy a convention.

## Task tracking

GitHub Issues and Projects are the default source of truth for task status when enabled. Local `tasks/` is for durable plans, milestones, research, and reports—not a mirrored todo/doing/done board. Reference work with real issue numbers, e.g. `Closes #123`.

## CI contract

The template CI must execute real checks. The baseline quality gate runs bootstrap end-to-end tests, shell linting, Markdown linting, and GitHub Actions workflow validation on every pull request and push to the default branch. Add language-specific lint, test, and build jobs only when the project has the corresponding toolchain and commands configured. A placeholder or commented-out command is not a passing check. Run the same baseline locally with the tools listed in `scripts/validate-repo.sh`.

## Customization

This template is intentionally domain- and language-neutral. Add project-specific rules under `.ai/context/`, `.ai/rules/`, and relevant workflow folders. Keep agent role contracts generic; adapt them to a specific coding harness only in that harness's configuration directory.

## License

MIT — see [LICENSE](LICENSE).
