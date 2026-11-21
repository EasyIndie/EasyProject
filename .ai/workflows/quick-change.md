# Quick Change workflow

Use for a small, isolated, reversible change with limited user impact.

1. **Inspect** repository status, relevant files, conventions, and existing tests.
2. **Bound** the change in one or two sentences; record any assumption.
3. **Implement** the smallest focused diff. Do not refactor adjacent code.
4. **Verify** with the narrowest relevant check (for example, formatter, targeted test, shell syntax, or link check).
5. **Review** the final diff for scope creep, secrets, and accidental edits.
6. **Handoff** summary, changed files, exact check results, and residual risks.

Escalate to Feature Development if behavior, public interfaces, or multiple components are affected. Escalate to Major Change if the change touches security boundaries, persistent data, or production operations.
