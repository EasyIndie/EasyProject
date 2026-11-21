# Specifications

Use `specs/` for non-trivial product requirements, acceptance criteria, and API/data contracts.

## When to create a spec

Create a spec when a change affects user-visible behavior, spans multiple components, changes a public interface, or has meaningful product ambiguity. For a typo, routine documentation update, or isolated low-risk fix, a short task description is enough.

## Suggested structure

```text
specs/<feature>/
  prd.md           problem, users, goals, scope, non-goals
  acceptance.md    observable acceptance criteria
  api.md           optional API or data contract
```

Use only the files the change needs. A small feature can keep the brief and acceptance criteria in one document.

## Minimum useful content

- Problem and intended user outcome
- In-scope and out-of-scope behavior
- Constraints, dependencies, and assumptions
- Observable acceptance criteria, including important failure cases

## Workflow

1. Check for an existing spec or issue before creating a duplicate.
2. Resolve material product questions with the human; do not invent requirements.
3. Link implementation work to the relevant GitHub Issue/PR when available.
4. Update the spec when the agreed behavior changes.

See [Feature Development](../.ai/workflows/feature-development.md) and [Major Change](../.ai/workflows/major-change.md).
