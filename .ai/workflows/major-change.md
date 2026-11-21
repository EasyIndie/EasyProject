# Major Change workflow

Use for architectural redesigns, breaking API/data changes, persistent-data migrations, security-boundary changes, major dependency/platform shifts, or high-impact production delivery.

1. **Discovery** — gather current-state evidence, stakeholders, constraints, threat/risk model, and failure scenarios.
2. **Decision** — document alternatives, trade-offs, and approval points in an ADR/design proposal.
3. **Migration plan** — define compatibility, backup, rollout stages, observability, rollback, and data-repair strategy.
4. **Decomposition** — split work into independently reviewable changes with explicit dependencies and owners.
5. **Implementation** — use staged flags or compatibility layers where appropriate; keep each change reversible where possible.
6. **Verification** — test migration on representative data, failure paths, rollback, security, performance, and operational readiness.
7. **Independent review** — require focused review of design, implementation, and operational risks.
8. **Human gate** — obtain explicit authorization before production deployment, irreversible migration, security-setting changes, or external publication.
9. **Release and monitor** — follow the approved rollout plan, monitor defined signals, and record outcomes.

Do not infer approval from silence or from approval of an earlier planning document.
