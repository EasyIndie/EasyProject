# Harness adapter guidance

Adapters translate the shared task/handoff envelopes into a harness's native interface. This repository currently defines contracts and mapping guidance only; it does not ship executable Pi, Codex, or Claude Code launchers.

## Required adapter behavior

1. Validate the task envelope before invoking a harness.
2. Read the repository's `AGENTS.md` and applicable role contract.
3. Pass objective, context, constraints, and acceptance criteria without dropping fields.
4. Preserve the harness's existing login, API key, subscription, and model configuration. Never serialize credentials into task/handoff JSON, logs, artifacts, or Git.
5. Enforce task permissions outside the model prompt where possible. Prompt text alone is not a security boundary.
6. Capture exact commands and outcomes; distinguish skipped from passed.
7. Emit a handoff conforming to `schemas/handoff.schema.json`, including unresolved risks.

## Pi

- Map the task envelope into a Pi session/task prompt and the selected role instructions.
- Use Pi's configured provider, model, extensions, and authentication as managed by the user.
- Do not assume that tool availability implies permission; apply the task permission policy in the host runtime.
- Capture the session's final response and tool/command evidence in the handoff.

## Codex

- Map the task objective and constraints into a Codex CLI task invocation, with repository instructions loaded from `AGENTS.md`.
- Use the user's existing Codex authentication and model selection. Do not inject API keys or rewrite Codex configuration.
- Apply sandbox and approval settings from the host policy; do not silently select a less restrictive mode.
- Record tests and command outcomes, not merely the final textual summary.

## Claude Code

- Map the task objective and constraints into a Claude Code task, loading `CLAUDE.md` which delegates to `AGENTS.md`.
- Preserve the user's configured authentication, provider endpoint, and model. Never copy credentials into project files.
- Apply tool permissions and approval settings through the harness/runtime configuration.
- Record file changes, verification evidence, and unresolved risks in the handoff.

## Capability differences

Harnesses do not necessarily expose identical tools, context windows, approval controls, or structured output. An adapter must report unsupported capabilities and must not claim parity. If a permission cannot be enforced, fail closed for that capability or request human intervention.
