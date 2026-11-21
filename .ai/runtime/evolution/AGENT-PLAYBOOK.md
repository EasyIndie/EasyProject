# Local template maintenance and self-evolution playbook

This guide is the default operating procedure when an Agent is asked to maintain **the EasyProject template repository itself**. It is designed so a freshly cloned checkout can be used immediately without manually assembling a multi-step prompt.

## 1. Decide which operating mode applies

First inspect `git remote -v`, the current branch, and repository files.

- **Template maintenance mode** applies only when the checkout's `origin` is the canonical `EasyIndie/EasyProject` repository (HTTPS or SSH), or the human explicitly says this is the canonical template checkout. Use this guide and the isolated Evolution runtime.
- **Generated-project mode** applies to repositories created from the template, forks, or unrelated projects. Follow their local `AGENTS.md` and normal workflows. Do not run EasyProject's self-evolution scripts merely because they exist in a copied repository.
- If the origin is ambiguous, ask one concise clarification before creating an Evolution run.

Never infer canonical identity from the directory name alone.

## 2. First local session: Agent does the setup checks

After the human clones the repository and opens an Agent in the repository root, the Agent should do the following automatically:

1. Read root `AGENTS.md`, `.ai/README.md`, this playbook, and the relevant runtime/adapter docs.
2. Inspect `git status --short`, current branch, `git remote -v`, and `git log -1 --oneline`. Preserve all local changes.
3. If the working tree is clean and the current branch is `main`, fetch and fast-forward from `origin/main`; never reset, force-pull, or discard local work. If there are local changes or a non-main branch, report that and do not silently switch branches.
4. Check Python 3, `jsonschema`, Git, and the requested Agent CLI. Do not inspect credential files or print environment secrets.
5. Run the non-mutating preflight for the selected supported Evolution harness:
   ```bash
   python3 scripts/evolution.py doctor --harness codex
   # or: --harness claude-code, --harness pi
   ```
6. If a prerequisite is missing, report the exact missing item and give the shortest safe install/configuration instruction. Do not install software, change shell profiles, or alter user-level configuration without permission.
7. Do not start a write-enabled Agent merely because the checkout was opened. Start only after the human's task/goal is clear or the human has asked the Agent to discover and propose improvements.

The preflight is read-only. It verifies checkout cleanliness, Python dependency, executable, and CLI version; it does not prove authentication or inspect credentials.

## 3. Recommended local layout and isolation

Keep the canonical checkout as the **Stable Checkout**. Do not let a coding Agent edit it.

For a checkout at `~/AIWorkspace/EasyProject`, Evolution creates sibling runtime data:

```text
~/AIWorkspace/
├── EasyProject/                         # Stable Checkout; clean and protected
└── .EasyProject-evolution/
    └── <run-id>/
        ├── candidate/                    # Candidate branch/worktree
        ├── runtime/                      # manifest, plan, task, journal, logs, evidence
        │   └── orchestrator/
        └── .candidate-agent-worktrees/   # nested coding-Agent worktrees
```

The candidate is based on the stable checkout's exact HEAD. Its orchestrator launches the coding Agent in a second, nested worktree. Mutable task data and evidence stay outside both source worktrees. Do not move these directories into the template or candidate.

This is Git worktree isolation, **not an OS security sandbox**. The task envelope's permission fields are not, by themselves, operating-system enforcement. Never describe the current runner as a VM/container sandbox.

## 4. Harness capability and role routing

| Harness | Current supported use in Evolution | Recommended responsibility |
|---|---|---|
| Pi Agent | Supported Evolution harness; write tasks require the explicit `harness_options.pi_unsandboxed_write=true` acknowledgement | Implementation in the nested Agent worktree when no write-capable CLI with a real sandbox is installed; planning and review |
| Codex CLI | Supported write-capable Evolution harness | Implementation in the nested Agent worktree |
| Claude Code CLI | Supported write-capable Evolution harness | Implementation in the nested Agent worktree |

Use the user's existing local authentication/model setup. Do not copy API keys, OAuth tokens, credential stores, or provider configuration into the repository, task envelope, manifest, logs, or worktree.

Do not relabel a tool allowlist as an OS sandbox. Pi's `--tools` allowlist is a capability restriction, not a filesystem boundary: a Pi write task therefore requires the explicit Task Envelope acknowledgement `harness_options.pi_unsandboxed_write=true`. A self-evolution goal records it in the generated envelope, and an approved discovery artifact must already contain it or Evolution rejects the run. Network, secret, and external-side-effect denial remain policy constraints on this path rather than enforced boundaries, so prefer Codex (`workspace-write`) when the task needs a real boundary.

## 5. Start an isolated self-evolution run

For a clearly scoped human-requested goal, choose a unique run ID (letters, digits, dot, underscore, and hyphen; 1–48 characters) and an allowlisted acceptance check.

First run preflight:

```bash
python3 scripts/evolution.py doctor --harness codex
```

Then start the task:

```bash
python3 scripts/evolution.py start \
  --id local-workflow-001 \
  --harness codex \
  --goal "Implement the explicitly agreed EasyProject template improvement" \
  --check python-unittest
```

Use `--harness claude-code` when Claude Code is selected and available. `--harness pi` works too, but Pi has no OS-level sandbox: the generated envelope records `harness_options.pi_unsandboxed_write=true` and the run is worktree-isolated rather than sandboxed.

Supported acceptance checks are `python-unittest`, `pytest`, `swift-test`, `cargo-test`, `npm-test`, `go-test`, and `repo-validation`. Choose only checks relevant to the actual change.

For discovery-led maintenance, run the read-only discovery command and inspect its evidence before promoting any candidate. Test fixtures and markers inside quoted strings are deliberately not reported; treat that as a precision trade-off, not as proof of a clean backlog:

```bash
python3 scripts/agent-discover.py --output ../easyproject-discovery.json
```

A write-enabled discovery task must be explicitly reviewed and promoted by a human using `scripts/agent-task-approve.py`. Never auto-approve discoveries or automatically turn every TODO/FIXME into a coding task. Follow [the discovery contract](../discovery/README.md).

## 6. Review, approve, integrate, and verify

When the run reaches `awaiting_review`, stop and inspect the report, handoff, full diff, acceptance-check logs, and review evidence. Use the external runtime directory; do not assume an Agent's success message means the task is complete.

```bash
python3 scripts/evolution.py report --id local-workflow-001
python3 scripts/evolution.py run --id local-workflow-001 status
python3 scripts/evolution.py run --id local-workflow-001 approve
python3 scripts/evolution.py run --id local-workflow-001 integrate
```

Approval and integration are separate gates. Integration creates a local commit on the candidate branch only. If a task is cancelled, timed out, blocked, or has failed checks, inspect the preserved logs/evidence before retrying. Do not delete the worktree or runtime directory as a cleanup shortcut.

Run the repository checks in the candidate after integration:

```bash
cd ../.EasyProject-evolution/local-workflow-001/candidate
python3 -m unittest discover --start-directory tests --pattern 'test_*.py'
bash scripts/validate-repo.sh
python3 scripts/check-template-cleanliness.py
git status --short
git diff <stable-base-sha>...HEAD
```

If full validation tools are unavailable, report them as not run; do not claim success. Check that no runtime artifacts, secrets, machine-specific files, or unrelated changes entered the candidate.

## 7. Return changes to the canonical template

The Evolution runtime deliberately does not push, create PRs, merge, change branch protection, publish, or deploy.

After human review of the candidate diff and test evidence:

1. Confirm the candidate branch and base SHA in the manifest.
2. Push the candidate branch only when the human has authorized remote publication.
3. Open a focused PR against `main`, including the goal, design, test commands/results, risks, and candidate base SHA.
4. Wait for required CI/review. Merge only with explicit human authorization.
5. After merge, update the Stable Checkout with a fast-forward pull. Keep the external run record for audit until the human decides it can be archived.

Never merge the candidate directly into the Stable Checkout as a shortcut. Never push from the Stable Checkout while it contains unreviewed local edits.

## 8. Resume an existing run instead of duplicating work

Before creating a new run, inspect the sibling `.EasyProject-evolution/` directory and ask the user for the run ID only if more than one plausible active run exists. For a known run:

```bash
python3 scripts/evolution.py report --id <run-id>
python3 scripts/evolution.py run --id <run-id> status
```

Resume only when the orchestrator reports a retryable state and the original task intent remains valid. Re-check the stable base and current candidate diff. Do not create a second run to hide or overwrite an incomplete run.

## 9. One-line entry prompt for a freshly cloned repository

The human can simply tell any compatible Agent:

> Read `AGENTS.md`. Determine whether this is the canonical EasyProject template checkout or a project generated from it. If it is the template, follow `.ai/runtime/evolution/AGENT-PLAYBOOK.md`: inspect the local environment and existing runs, perform non-mutating preflight, then recommend or continue the safest isolated workflow. Do not modify the Stable Checkout, expose credentials, bypass harness restrictions, or push/merge/deploy without explicit approval.

The repository instructions should make this behavior discoverable even when this prompt is not supplied.
