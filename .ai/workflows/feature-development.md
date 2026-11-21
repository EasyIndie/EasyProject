# Feature Development workflow

Use for new or changed user-visible behavior, public interfaces, or work spanning multiple components.

1. **Understand** the user problem, desired outcome, constraints, non-goals, and dependencies.
2. **Specify** acceptance criteria. Create a PRD/spec only when behavior or scope is non-trivial.
3. **Design** component boundaries, interfaces, data flow, failure behavior, and compatibility. Create an ADR for durable consequential decisions.
4. **Plan** a sequence of small implementation tasks; use GitHub Issues/Projects as status source of truth when enabled.
5. **Implement** in focused commits; add tests alongside behavior.
6. **Verify** acceptance criteria, relevant automated checks, and important failure/boundary cases.
7. **Review** the complete diff independently; address blocking findings.
8. **Handoff/release** with evidence, migration notes, known risks, and rollback considerations.

Escalate to Major Change for data migrations, breaking changes, security-boundary changes, or production rollout with significant blast radius.
