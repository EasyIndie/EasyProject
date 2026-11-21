# Harness adapters

The repository provides a local CLI dispatcher at `scripts/agent-run.py`. It validates the shared task envelope, invokes an installed harness, preserves user-managed authentication/model configuration, and writes a normalized handoff draft plus raw logs.

## Usage

From the repository root:

```bash
python3 -m pip install jsonschema
python3 scripts/agent-run.py --task .ai/runtime/examples/task.json --harness codex --output .agent-runs/example.json
```

Supported harness names: `pi`, `codex`, and `claude-code`. The corresponding executable must already be installed and authenticated on PATH. The dispatcher never installs CLIs, logs in, reads credential stores, or changes model/provider settings.

## Permission mapping

| Capability | Pi | Codex CLI | Claude Code |
|---|---|---|---|
| Read-only | Built-in read tools allowlist | `read-only` sandbox | `plan` permission mode |
| Repository write | Disabled by default; the explicit `--allow-unsandboxed-pi-write` CLI flag adds `edit,write,bash` | `workspace-write` sandbox with `on-request` approval | `default` permission mode; relies on user's configured permission policy |
| Network | Rejected | Rejected by this adapter | Rejected by this adapter |
| Secrets | Rejected | Rejected | Rejected |
| External side effects | Rejected | Rejected | Rejected |

This is intentionally conservative. The adapter does not provide a universal security sandbox. Codex enforces workspace sandboxing at the OS boundary. Claude Code's default permission mode relies on the user's configured permissions and may prompt. Pi's `--tools` allowlist is a capability restriction, not a filesystem sandbox, so write access is never granted implicitly: a write task must be launched with `--allow-unsandboxed-pi-write`. This is a deliberate unsafe override, not an OS sandbox; the Worktree does not prevent host access. With that acknowledgement Pi receives `edit`, `write`, and `bash`; without it the task is rejected. Network denial remains advisory for Pi because the adapter cannot enforce it.

## Output and review

With `--output path.json`, the dispatcher writes:
- `path.json`: a handoff draft conforming to the shared handoff schema.
- `path.json.stdout.txt` and `path.json.stderr.txt`: raw harness output.

The handoff status is `partial` when the CLI exits successfully and `failed` otherwise. A zero exit code does not prove the task's acceptance criteria. The draft deliberately records verification as `not-run`; a human or orchestrator must inspect the diff, logs, and tests before changing the status to `completed`.

Timeouts default to the task envelope's `timeout_minutes` and can be overridden with `--timeout`. A timeout exits with code 124. The dispatcher rejects network access, secret access, and external side effects until a separately enforceable policy integration exists.

## Harness notes

- **Pi:** Uses print/JSON mode. Read-only tasks get the `read,grep,find,ls` allowlist; explicitly overridden write tasks (`--allow-unsandboxed-pi-write`) also get `edit,write,bash`. It preserves Pi's configured provider, model, and authentication. Run Pi write tasks only inside an isolated worktree.
- **Codex:** Uses `codex exec --json`, with `read-only` or `workspace-write` sandbox and `on-request` approval. It preserves the user's existing Codex authentication and model configuration.
- **Claude Code:** Uses `claude -p --output-format json`; read-only tasks use plan mode, while write tasks use default permission mode and preserve user-configured permission rules. Never add `--dangerously-skip-permissions` or bypass permission modes.

## Limitations

This first adapter version is a one-shot local process dispatcher, not a persistent session manager or multi-agent orchestrator. It does not parse provider-specific event streams into semantic tool traces, independently discover changed files, or evaluate acceptance criteria. Do not use it for unattended production deployment or other irreversible actions.
