# Branch rules

Use short-lived, focused branches where practical. Branch lifetime is a guideline, not a hard limit; split work when a branch becomes difficult to review.

## Naming

| Prefix | Use |
|---|---|
| `feature/` | New behavior |
| `fix/` | Bug fix |
| `docs/` | Documentation |
| `refactor/` | Behavior-preserving refactor |
| `chore/` | Maintenance and configuration |
| `test/` | Test-only changes |

Use lowercase kebab-case names.

## Safety

- Start from the latest default branch unless the task explicitly targets another branch.
- Do not commit directly to a protected default branch.
- Never force-push the default branch or rewrite shared history.
- Use `--force-with-lease` only on a branch you own and only when necessary.
- Preserve uncommitted user changes.
- Do not delete branches or merge PRs without the appropriate authorization.

## Pull requests

Keep each PR focused. Describe the change, motivation, verification, and known risks. Link real issue numbers using GitHub syntax such as `Closes #123` or `Refs #123`; never invent task identifiers.

## Agent guidance

Before creating a branch, inspect the current branch and working tree. If there are uncommitted changes, do not overwrite or discard them. Follow repository protection and review requirements.
