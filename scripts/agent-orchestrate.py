#!/usr/bin/env python3
"""Run a dependency-aware, serial queue of local Agent Task Envelopes.

This is a lightweight local orchestrator, not a sandbox or a distributed queue.
A task is not considered complete until a human explicitly approves its handoff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT / "scripts"))
ROOT = CODE_ROOT
RUNNER = CODE_ROOT / "scripts/agent-run.py"
TERMINAL = {"completed", "failed", "blocked", "cancelled"}
ACCEPTANCE_CHECK_TIMEOUT_SECONDS = 900


def acceptance_command(check_id: str) -> list[str]:
    """Resolve a schema-allowlisted check ID to a fixed argv; never invoke a shell."""
    commands = {
        "python-unittest": [sys.executable, "-m", "unittest", "discover", "--start-directory", "tests", "--pattern", "test_*.py"],
        "pytest": ["pytest"],
        "swift-test": ["swift", "test"],
        "cargo-test": ["cargo", "test"],
        "npm-test": ["npm", "test"],
        "go-test": ["go", "test", "./..."],
        "repo-validation": ["bash", "scripts/validate-repo.sh"],
    }
    if check_id not in commands:
        raise ValueError(f"Unsupported acceptance check: {check_id}")
    return commands[check_id]


def stop_command_tree(process: subprocess.Popen[str]) -> tuple[str, str]:
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            process.terminate()
        except OSError:
            pass
    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               text=True, capture_output=True, check=False)
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                process.kill()
            except OSError:
                pass
        return process.communicate()


def run_command_controlled(argv: list[str], workspace: Path, timeout_seconds: int,
                           cancel_file: Path | None = None,
                           environment: dict[str, str] | None = None) -> tuple[int, str, str, str | None]:
    options: dict[str, object] = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    process = subprocess.Popen(
        argv, cwd=workspace, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment if environment is not None else os.environ.copy(), **options,
    )
    started = time.monotonic()
    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.2)
            return process.returncode or 0, stdout, stderr, None
        except subprocess.TimeoutExpired:
            if cancel_file and cancel_file.is_file():
                stdout, stderr = stop_command_tree(process)
                return 130, stdout, stderr, "cancelled"
            if time.monotonic() - started >= timeout_seconds:
                stdout, stderr = stop_command_tree(process)
                return 124, stdout, stderr, "timeout"


def run_acceptance_checks(check_ids: list[str], workspace: Path,
                          runs_dir: Path, task_id: str, attempt: int,
                          cancel_file: Path | None = None,
                          require_sandbox: bool = False,
                          sandbox_profile: Path | None = None,
                          task_permissions: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run only fixed, allowlisted test commands and persist their outputs."""
    if not check_ids:
        return {"status": "not_configured", "results": []}
    output_dir = runs_dir / task_id / "checks" / f"attempt-{attempt}"
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for check_id in check_ids:
        argv = acceptance_command(check_id)
        stdout_path = output_dir / f"{check_id}.stdout.txt"
        stderr_path = output_dir / f"{check_id}.stderr.txt"
        environment = None
        check_timeout = ACCEPTANCE_CHECK_TIMEOUT_SECONDS
        sandbox_evidence = None
        if shutil.which(argv[0]) is None:
            stdout, stderr, exit_code, result = "", f"Executable not found: {argv[0]}", None, "not_found"
        else:
            if require_sandbox:
                if sandbox_profile is None or task_permissions is None:
                    raise ValueError("Sandboxed acceptance checks require the trusted profile and task permissions.")
                from sandbox_runtime import SandboxManager
                argv, environment, sandbox_evidence = SandboxManager().build_command(
                    argv, sandbox_profile, f"{task_id}-check-{attempt}-{check_id}",
                    workspace, runs_dir / "sandbox-runtime" / task_id / check_id,
                    task_permissions,
                )
                check_timeout = min(check_timeout, sandbox_evidence["timeout_seconds"])
            exit_code, stdout, stderr, termination = run_command_controlled(
                argv, workspace, check_timeout, cancel_file, environment,
            )
            if termination == "cancelled":
                result = "cancelled"
            elif termination == "timeout":
                stderr += f"\\nTimed out after {ACCEPTANCE_CHECK_TIMEOUT_SECONDS} seconds."
                result = "timeout"
            else:
                result = "passed" if exit_code == 0 else "failed"
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        results.append({
            "check_id": check_id,
            "argv": argv,
            "result": result,
            "exit_code": exit_code,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "sandbox_status": sandbox_evidence["status"] if sandbox_evidence else "not-requested",
            "sandbox_backend": sandbox_evidence.get("backend") if sandbox_evidence else None,
        })
        if result == "cancelled":
            return {"status": "cancelled", "results": results}
    status = "passed" if all(item["result"] == "passed" for item in results) else "failed"
    return {"status": status, "results": results}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_plan(path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read plan JSON: {exc}") from exc
    if not isinstance(plan, dict) or plan.get("protocol_version") != "1.0":
        raise ValueError("Plan protocol_version must be '1.0'.")
    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Plan must contain a non-empty tasks array.")
    ids: set[str] = set()
    for item in tasks:
        if not isinstance(item, dict):
            raise ValueError("Each plan task must be an object.")
        task_id = item.get("task_id")
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", task_id) or task_id in ids:
            raise ValueError(f"Invalid or duplicate task_id: {task_id!r}")
        ids.add(task_id)
        if not isinstance(item.get("task_file"), str) or not item["task_file"]:
            raise ValueError(f"{task_id}: task_file is required.")
        if item.get("harness", "codex") not in {"pi", "codex", "claude-code"}:
            raise ValueError(f"{task_id}: unsupported harness.")
        deps = item.get("depends_on", [])
        if not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps):
            raise ValueError(f"{task_id}: depends_on must be an array of task IDs.")
        attempts = item.get("max_attempts", 1)
        if not isinstance(attempts, int) or isinstance(attempts, bool) or not 1 <= attempts <= 5:
            raise ValueError(f"{task_id}: max_attempts must be between 1 and 5.")
    by_id = {item["task_id"]: item for item in tasks}
    for item in tasks:
        for dep in item.get("depends_on", []):
            if dep not in by_id:
                raise ValueError(f"{item['task_id']}: unknown dependency {dep!r}.")
            if dep == item["task_id"]:
                raise ValueError(f"{dep}: task cannot depend on itself.")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError(f"Dependency cycle detected at {task_id}.")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dep in by_id[task_id].get("depends_on", []):
            visit(dep)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id)
    return plan


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def initial_state(plan: dict[str, Any], use_worktrees: bool = False,
                  sandbox_required: bool = False, sandbox_profile: str | None = None,
                  sandbox_profile_sha256: str | None = None) -> dict[str, Any]:
    return {
        "protocol_version": "1.0",
        "worktrees_enabled": use_worktrees,
        "sandbox_required": sandbox_required,
        "sandbox_profile": sandbox_profile,
        "sandbox_profile_sha256": sandbox_profile_sha256,
        "updated_at": now(),
        "tasks": {
            item["task_id"]: {
                "task_id": item["task_id"],
                "status": "pending", "attempts": 0, "handoff": None,
                "last_exit_code": None, "worktree": None, "base_commit": None, "updated_at": now()
            }
            for item in plan["tasks"]
        },
    }



def git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise ValueError("git command failed: " + result.stderr.strip())
    return result.stdout.strip()


def prepare_worktree(repo: Path, runs_dir: Path, task_id: str,
                     record: dict[str, Any]) -> Path:
    """Create or validate a detached worktree dedicated to one task."""
    if record.get("worktree"):
        path = Path(record["worktree"]).resolve()
        if not path.is_dir():
            raise ValueError(task_id + ": recorded worktree is missing; inspect journal before recovery.")
        top = Path(git_output(path, "rev-parse", "--show-toplevel")).resolve()
        common = Path(git_output(path, "rev-parse", "--git-common-dir"))
        if not common.is_absolute():
            common = (path / common).resolve()
        else:
            common = common.resolve()
        expected_common = Path(git_output(repo, "rev-parse", "--git-common-dir"))
        if not expected_common.is_absolute():
            expected_common = (repo / expected_common).resolve()
        else:
            expected_common = expected_common.resolve()
        if top != path or common != expected_common:
            raise ValueError(task_id + ": recorded path is not a worktree of this repository.")
        return path

    run_key = hashlib.sha256(str(runs_dir.resolve()).encode("utf-8")).hexdigest()[:12]
    path = (repo.parent / ("." + repo.name + "-agent-worktrees") / run_key / task_id).resolve()
    if path.exists():
        raise ValueError(task_id + ": worktree path already exists but is not recorded: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    base_commit = git_output(repo, "rev-parse", "HEAD")
    result = subprocess.run(
        ["git", "worktree", "add", "--detach", str(path), base_commit],
        cwd=repo, text=True, capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError(task_id + ": cannot create worktree: " + result.stderr.strip())
    record["worktree"] = str(path)
    record["base_commit"] = base_commit
    return path


def collect_change_evidence(repo: Path, base_commit: str, task_id: str,
                            runs_dir: Path, persist: bool = True,
                            automated_checks: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture a deterministic review snapshot without staging or committing files."""
    status = git_output(repo, "status", "--porcelain=v1", "--untracked-files=all")
    changed = git_output(repo, "diff", "--name-only", base_commit).splitlines()
    untracked = git_output(repo, "ls-files", "--others", "--exclude-standard").splitlines()
    changed_files = sorted(set(changed + untracked))
    diff_check = subprocess.run(
        ["git", "diff", "--check", base_commit], cwd=repo,
        text=True, capture_output=True, check=False,
    )
    check_output = diff_check.stdout + diff_check.stderr
    check_failed = diff_check.returncode != 0
    diff = git_output(repo, "diff", "--binary", base_commit)
    for relative_path in untracked:
        extra = subprocess.run(
            ["git", "diff", "--no-index", "--binary", "--", "/dev/null", relative_path],
            cwd=repo, text=True, capture_output=True, check=False,
        )
        if extra.returncode not in {0, 1}:
            raise ValueError("Cannot capture untracked file diff: " + relative_path)
        diff += extra.stdout
        extra_check = subprocess.run(
            ["git", "diff", "--no-index", "--check", "--", "/dev/null", relative_path],
            cwd=repo, text=True, capture_output=True, check=False,
        )
        if extra_check.returncode not in {0, 1}:
            raise ValueError("Cannot check untracked file whitespace: " + relative_path)
        if extra_check.returncode == 1 and (extra_check.stdout or extra_check.stderr):
            check_failed = True
            check_output += extra_check.stdout + extra_check.stderr
    stat = git_output(repo, "diff", "--stat", base_commit)
    fingerprint = hashlib.sha256(
        (diff + "\\0" + "\n".join(changed_files)).encode("utf-8")
    ).hexdigest()
    evidence_dir = runs_dir / task_id
    diff_path = evidence_dir / "review.diff"
    if persist:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        diff_path.write_text(diff, encoding="utf-8")
    evidence = {
        "protocol_version": "1.0",
        "task_id": task_id,
        "base_commit": base_commit,
        "captured_at": now(),
        "changed_files": changed_files,
        "diff_stat": stat,
        "diff_check": {
            "result": "failed" if check_failed else "passed",
            "output": check_output,
        },
        "fingerprint": fingerprint,
        "diff_path": str(diff_path),
        "acceptance": {
            "status": "pending_human_review",
            "criteria_source": "Task Envelope acceptance_criteria",
            "automated_checks": automated_checks or {"status": "not_configured", "results": []},
            "note": "Automated checks supplement but do not certify natural-language acceptance criteria.",
        },
    }
    evidence_path = evidence_dir / "review-evidence.json"
    if persist:
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evidence["evidence_path"] = str(evidence_path)
    return evidence


def verify_change_evidence(repo: Path, record: dict[str, Any]) -> None:
    evidence_path = record.get("review_evidence")
    if not evidence_path or not Path(evidence_path).is_file():
        raise ValueError("Review evidence is missing; rerun the evidence capture before approval.")
    evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    current = collect_change_evidence(
        repo, evidence["base_commit"], evidence["task_id"],
        Path(evidence_path).parent.parent, persist=False,
    )
    if current["fingerprint"] != evidence.get("fingerprint"):
        raise ValueError("Workspace changed after review evidence was captured; inspect and recapture before approval.")
    if evidence.get("diff_check", {}).get("result") != "passed":
        raise ValueError("git diff --check failed; fix whitespace errors before approval.")
    if evidence.get("acceptance", {}).get("automated_checks", {}).get("status") == "failed":
        raise ValueError("Configured acceptance checks failed; fix the task and rerun before approval.")



def publish_review_artifact(evidence: dict[str, Any], runs_dir: Path,
                           task_id: str, attempt: int) -> dict[str, Any]:
    """Publish a portable immutable review snapshot after a sandboxed task has stopped."""
    from artifact_broker import export_artifact

    source_dir = runs_dir / task_id / f".artifact-source-attempt-{attempt}"
    if source_dir.exists():
        raise ValueError(f"Artifact staging directory already exists: {source_dir}")
    source_dir.mkdir(parents=True)
    try:
        diff_source = Path(evidence["diff_path"])
        if diff_source.is_symlink() or not diff_source.is_file():
            raise ValueError("Review diff is missing or unsafe; cannot publish review artifact.")
        shutil.copyfile(diff_source, source_dir / "review.diff")
        portable = dict(evidence)
        portable["diff_path"] = "review.diff"
        portable.pop("evidence_path", None)
        acceptance = portable.get("acceptance", {})
        checks = acceptance.get("automated_checks", {})
        for item in checks.get("results", []):
            for key in ("stdout_path", "stderr_path"):
                if item.get(key):
                    item[key] = Path(item[key]).name
        (source_dir / "review-evidence.json").write_text(
            json.dumps(portable, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result = export_artifact(
            source_dir, runs_dir.parent / f"{runs_dir.name}.artifacts", task_id, "review-evidence",
            ["review.diff", "review-evidence.json"], evidence.get("base_commit"),
        )
        manifest = result["manifest"]
        return {
            "artifact_id": manifest["artifact_id"],
            "artifact_dir": result["artifact_dir"],
            "kind": manifest["kind"],
            "source_revision": manifest["source_revision"],
        }
    finally:
        shutil.rmtree(source_dir, ignore_errors=True)


def verify_review_artifact(record: dict[str, Any]) -> dict[str, Any]:
    """Verify immutable artifact integrity and bind it to the reviewed workspace evidence."""
    from artifact_broker import verify_artifact

    artifact = record.get("review_artifact")
    if not isinstance(artifact, dict) or not artifact.get("artifact_dir"):
        raise ValueError("Sandbox-required task is missing its immutable review artifact.")
    artifact_dir = Path(artifact["artifact_dir"])
    manifest = verify_artifact(artifact_dir)
    if (manifest.get("task_id") != record.get("task_id")
            or manifest.get("kind") != "review-evidence"
            or manifest.get("artifact_id") != artifact.get("artifact_id")):
        raise ValueError("Review artifact manifest does not match the task journal.")
    artifact_evidence = json.loads((artifact_dir / "review-evidence.json").read_text(encoding="utf-8"))
    evidence_path = record.get("review_evidence")
    if not evidence_path or not Path(evidence_path).is_file():
        raise ValueError("Original review evidence is missing.")
    original = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    if (artifact_evidence.get("task_id") != record.get("task_id")
            or artifact_evidence.get("fingerprint") != original.get("fingerprint")
            or artifact_evidence.get("base_commit") != original.get("base_commit")
            or manifest.get("source_revision") != original.get("base_commit")):
        raise ValueError("Immutable review artifact is not bound to the current task evidence.")
    return manifest


def resolve_task_path(task_file: str, runs_dir: Path) -> Path:
    """Resolve a task file from the repository or this run's external data directory."""
    candidate = Path(task_file)
    task_path = (candidate if candidate.is_absolute() else ROOT / candidate).resolve()
    allowed_roots = (ROOT.resolve(), runs_dir.resolve())
    if not any(task_path.is_relative_to(root) for root in allowed_roots):
        raise ValueError("task_file must stay inside the repository or the configured runs directory.")
    return task_path


def build_runner_command(task_path: Path, harness: str, output: Path, workspace: Path,
                         cancel_file: Path, allow_unsandboxed_pi_write: bool,
                         require_sandbox: bool = False,
                         sandbox_profile: Path | None = None) -> list[str]:
    """Build the runner argv; Pi's unsafe write opt-in comes only from the control plane."""
    command = [
        sys.executable, str(RUNNER), "--task", str(task_path),
        "--harness", harness, "--output", str(output), "--cwd", str(workspace),
        "--cancel-file", str(cancel_file),
    ]
    if harness == "pi" and allow_unsandboxed_pi_write:
        command.append("--allow-unsandboxed-pi-write")
    if require_sandbox:
        if sandbox_profile is None:
            raise ValueError("Sandbox-required orchestration needs a trusted profile path.")
        command.extend(["--require-sandbox", "--sandbox-profile", str(sandbox_profile)])
    return command


def run_plan(plan: dict[str, Any], runs_dir: Path, state: dict[str, Any], use_worktrees: bool,
             allow_unsandboxed_pi_write: bool = False, require_sandbox: bool = False,
             sandbox_profile: Path | None = None) -> int:
    if require_sandbox and not use_worktrees:
        raise ValueError("Sandbox-required orchestration requires task-specific worktrees.")
    by_id = {item["task_id"]: item for item in plan["tasks"]}
    state_path = runs_dir / "orchestrator-state.json"
    progress = True
    while progress:
        progress = False
        for item in plan["tasks"]:
            task_id = item["task_id"]
            record = state["tasks"][task_id]
            if record["status"] not in {"pending", "retryable"}:
                continue
            dependencies = item.get("depends_on", [])
            dependency_states = [state["tasks"][dep]["status"] for dep in dependencies]
            if any(status in {"failed", "blocked", "cancelled"} for status in dependency_states):
                record.update(status="blocked", updated_at=now())
                state["updated_at"] = now()
                save_state(state_path, state)
                progress = True
                continue
            if any(status != "completed" for status in dependency_states):
                continue
            try:
                task_path = resolve_task_path(item["task_file"], runs_dir)
            except ValueError as exc:
                raise ValueError(f"{task_id}: {exc}") from exc
            attempt = record["attempts"] + 1
            task_output = runs_dir / task_id / f"attempt-{attempt}.handoff.json"
            task_output.parent.mkdir(parents=True, exist_ok=True)
            workspace = prepare_worktree(ROOT, runs_dir, task_id, record) if use_worktrees else ROOT
            cancel_file = runs_dir / task_id / f"cancel-attempt-{attempt}.request"
            task_envelope = json.loads(task_path.read_text(encoding="utf-8"))
            harness = item.get("harness", "codex")
            if (
                harness == "pi"
                and task_envelope.get("permissions", {}).get("repository_write") is True
                and not allow_unsandboxed_pi_write
                and not require_sandbox
            ):
                raise ValueError(
                    f"{task_id}: Pi write requires the orchestrator's explicit "
                    "--allow-unsandboxed-pi-write control-plane flag."
                )
            command = build_runner_command(
                task_path, harness, task_output, workspace, cancel_file,
                allow_unsandboxed_pi_write, require_sandbox, sandbox_profile,
            )
            record.update(
                status="running", attempts=attempt, cancel_file=str(cancel_file),
                started_at=now(), updated_at=now(),
            )
            record.setdefault("first_started_at", record["started_at"])
            state["updated_at"] = now()
            save_state(state_path, state)
            result = subprocess.run(command, cwd=ROOT, check=False)
            record["last_exit_code"] = result.returncode
            record["handoff"] = str(task_output)
            sandbox_enforced = not require_sandbox
            sandbox_error = None
            if result.returncode == 0 and require_sandbox:
                try:
                    handoff = json.loads(task_output.read_text(encoding="utf-8"))
                    sandbox_enforced = handoff.get("artifacts", {}).get("sandbox_status") == "enforced"
                except (OSError, json.JSONDecodeError) as exc:
                    sandbox_error = f"Required sandbox handoff evidence is missing or invalid: {exc}"
                if not sandbox_enforced and sandbox_error is None:
                    sandbox_error = "Runner completed without an enforced sandbox status."
            automated_checks = {"status": "not_configured", "results": []}
            if result.returncode == 0 and sandbox_error is None:
                try:
                    automated_checks = run_acceptance_checks(
                        task_envelope.get("acceptance_checks", []), workspace,
                        runs_dir, task_id, attempt, cancel_file,
                        require_sandbox=require_sandbox,
                        sandbox_profile=sandbox_profile,
                        task_permissions=task_envelope.get("permissions", {}),
                    )
                except RuntimeError as exc:
                    automated_checks = {"status": "failed", "results": [], "error": str(exc)}
            record["automated_checks"] = automated_checks
            artifact_error = None
            if use_worktrees and record.get("base_commit"):
                evidence = collect_change_evidence(
                    workspace, record["base_commit"], task_id, runs_dir,
                    automated_checks=automated_checks,
                )
                record["review_evidence"] = evidence["evidence_path"]
                if (require_sandbox and sandbox_enforced
                        and automated_checks["status"] in {"passed", "not_configured"}):
                    try:
                        record["review_artifact"] = publish_review_artifact(
                            evidence, runs_dir, task_id, attempt,
                        )
                    except (OSError, ValueError, RuntimeError) as exc:
                        artifact_error = str(exc)
            if artifact_error:
                record.update(status="failed", termination_reason="artifact_export_failed",
                              artifact_error=artifact_error, finished_at=now())
            elif sandbox_error:
                record.update(status="failed", termination_reason="sandbox_evidence_invalid",
                              sandbox_error=sandbox_error, finished_at=now())
            elif result.returncode == 130 or automated_checks["status"] == "cancelled":
                record.update(status="cancelled", termination_reason="cancelled", finished_at=now())
            elif result.returncode == 0 and automated_checks["status"] in {"passed", "not_configured"}:
                # The adapter intentionally emits partial; only explicit human
                # approval may transition this task to completed.
                record["status"] = "awaiting_review"
                record["finished_at"] = now()
            elif attempt < item.get("max_attempts", 1):
                reason = (
                    "timeout" if result.returncode == 124
                    else "acceptance_checks_failed" if result.returncode == 0
                    else "process_failed"
                )
                record.update(status="retryable", termination_reason=reason, finished_at=now())
            else:
                reason = (
                    "timeout" if result.returncode == 124
                    else "acceptance_checks_failed" if result.returncode == 0
                    else "process_failed"
                )
                record.update(status="failed", termination_reason=reason, finished_at=now())
            record["updated_at"] = now()
            state["updated_at"] = now()
            save_state(state_path, state)
            progress = True
            # Stop after one actual agent invocation: review/approval is a gate.
            print(f"{task_id}: {record['status']} (exit={result.returncode}, checks={automated_checks['status']}, attempt={attempt})")
            return 1 if result.returncode or automated_checks["status"] not in {"passed", "not_configured"} else 0
    save_state(state_path, state)
    return 0


def request_cancel(task_id: str, state: dict[str, Any], runs_dir: Path) -> Path:
    """Write a cooperative cancellation marker for the currently running attempt."""
    record = state.get("tasks", {}).get(task_id)
    if record is None:
        raise ValueError(f"Unknown task_id: {task_id}")
    if record.get("status") != "running":
        raise ValueError(f"{task_id} is {record.get('status')}; only running tasks can be cancelled.")
    attempt = record.get("attempts", 0)
    if attempt < 1:
        raise ValueError(f"{task_id} has no active attempt to cancel.")
    marker = runs_dir / task_id / f"cancel-attempt-{attempt}.request"
    marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        marker.write_text(json.dumps({"task_id": task_id, "attempt": attempt, "requested_at": now()}), encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot create cancellation marker: {exc}") from exc
    return marker


def approve(task_id: str, state: dict[str, Any], state_path: Path) -> None:
    record = state["tasks"].get(task_id)
    if record is None:
        raise ValueError(f"Unknown task_id: {task_id}")
    if record["status"] != "awaiting_review":
        raise ValueError(f"{task_id} is {record['status']}; only awaiting_review tasks can be approved.")
    handoff_path = Path(record["handoff"])
    if not handoff_path.is_file():
        raise ValueError(f"Handoff file is missing: {handoff_path}")
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    if handoff.get("task_id") != task_id:
        raise ValueError("Handoff task_id does not match the requested task.")
    if handoff.get("status") == "failed":
        raise ValueError("A failed handoff cannot be approved.")
    if record.get("automated_checks", {}).get("status") == "failed":
        raise ValueError("Configured acceptance checks failed; task cannot be approved.")
    if state.get("sandbox_required", False):
        verify_review_artifact(record)
    if record.get("worktree"):
        verify_change_evidence(Path(record["worktree"]), record)
        record.update(status="approved", approved_at=now(), updated_at=now())
    else:
        record.update(status="completed", approved_at=now(), updated_at=now())
    state["updated_at"] = now()
    save_state(state_path, state)


def git_result(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=False
    )


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    return git_result(repo, "merge-base", "--is-ancestor", ancestor, descendant).returncode == 0


def integrate_task(repo: Path, task_id: str, state: dict[str, Any],
                   state_path: Path) -> None:
    """Commit an approved worktree result and cherry-pick it onto the current clean branch."""
    record = state.get("tasks", {}).get(task_id)
    if record is None:
        raise ValueError(f"Unknown task_id: {task_id}")
    if record.get("status") not in {"approved", "integration_conflict"}:
        raise ValueError(f"{task_id} is {record.get('status')}; approve it before integration.")

    branch = git_output(repo, "branch", "--show-current")
    if not branch:
        raise ValueError("Target repository is in detached HEAD state; check out a branch before integration.")
    target_head = git_output(repo, "rev-parse", "HEAD")

    if record.get("integration_state") == "conflict":
        if git_result(repo, "rev-parse", "--verify", "CHERRY_PICK_HEAD").returncode == 0:
            raise ValueError(
                "Cherry-pick is still in progress. Resolve conflicts, run "
                "'git cherry-pick --continue', then rerun --integrate."
            )
        parent = record.get("integration_parent")
        subject = record.get("integration_subject")
        head_parent = git_result(repo, "rev-parse", "HEAD^")
        head_subject = git_result(repo, "show", "-s", "--format=%s", "HEAD")
        if (parent and head_parent.returncode == 0 and head_parent.stdout.strip() == parent
                and head_subject.returncode == 0 and head_subject.stdout.strip() == subject):
            record.update(
                status="completed", integration_state="completed",
                integrated_at=now(), target_branch=branch, target_commit=target_head,
            )
            state["updated_at"] = now()
            save_state(state_path, state)
            return

    if git_output(repo, "status", "--porcelain=v1"):
        raise ValueError("Target repository must have a clean working tree before integration.")
    worktree_value = record.get("worktree")
    if not worktree_value:
        raise ValueError("Task has no isolated worktree; integration requires --worktrees.")
    worktree = Path(worktree_value).resolve()
    if not worktree.is_dir():
        raise ValueError("Recorded task worktree is missing.")
    base_commit = record.get("base_commit")
    if not base_commit:
        raise ValueError("Task journal is missing base_commit.")
    if not is_ancestor(repo, base_commit, target_head):
        raise ValueError("Target branch no longer contains the task base commit; rebase/recreate the task deliberately.")

    verify_change_evidence(worktree, record)
    if state.get("sandbox_required", False):
        verify_review_artifact(record)
    worktree_head = git_output(worktree, "rev-parse", "HEAD")
    if not is_ancestor(worktree, base_commit, worktree_head):
        raise ValueError("Task worktree HEAD is not based on its recorded base commit.")

    # Agent harnesses may create one or more commits inside their detached
    # worktree. Collapse the complete reviewed tree back onto the recorded base
    # so the integration commit cannot omit earlier agent commits.
    if git_result(worktree, "symbolic-ref", "-q", "HEAD").returncode == 0:
        raise ValueError("Task worktree is no longer detached; inspect it and restore a detached HEAD before integration.")
    add_result = git_result(worktree, "add", "-A", "--", ".")
    if add_result.returncode:
        raise ValueError("Cannot stage approved worktree changes: " + add_result.stderr.strip())
    reset_result = git_result(worktree, "reset", "--soft", base_commit)
    if reset_result.returncode:
        raise ValueError("Cannot normalize task commits to the recorded base: " + reset_result.stderr.strip())

    evidence = json.loads(Path(record["review_evidence"]).read_text(encoding="utf-8"))
    staged_files = git_output(worktree, "diff", "--cached", "--name-only").splitlines()
    if sorted(set(staged_files)) != sorted(evidence.get("changed_files", [])):
        raise ValueError("Staged file manifest differs from reviewed evidence; recapture and approve the changes again.")
    cached_check = git_result(worktree, "diff", "--cached", "--check")
    if cached_check.returncode:
        raise ValueError("Staged changes failed git diff --cached --check: " + cached_check.stdout + cached_check.stderr)

    staged = git_result(worktree, "diff", "--cached", "--quiet")
    if staged.returncode not in {0, 1}:
        raise ValueError("Cannot inspect staged changes: " + staged.stderr.strip())
    if staged.returncode == 1:
        commit_result = git_result(worktree, "commit", "-m", f"Agent task {task_id}")
        if commit_result.returncode:
            raise ValueError("Cannot create integration commit: " + commit_result.stdout + commit_result.stderr)
    agent_commit = git_output(worktree, "rev-parse", "HEAD")

    if agent_commit == base_commit:
        record.update(
            status="completed", integration_state="no_changes",
            integrated_at=now(), target_branch=branch, target_commit=target_head,
        )
        state["updated_at"] = now()
        save_state(state_path, state)
        return

    if git_output(repo, "rev-parse", "HEAD") != target_head:
        raise ValueError("Target branch moved during integration; inspect the repository and retry.")
    subject = f"Agent task {task_id}"
    cherry_pick = git_result(repo, "cherry-pick", agent_commit)
    if cherry_pick.returncode:
        record.update(
            status="integration_conflict", integration_state="conflict",
            integration_commit=agent_commit, integration_parent=target_head,
            integration_subject=subject,
            integration_output=cherry_pick.stdout + cherry_pick.stderr, updated_at=now(),
        )
        state["updated_at"] = now()
        save_state(state_path, state)
        raise ValueError(
            "Cherry-pick stopped with a conflict. The conflict state is preserved. "
            "Resolve it manually, run 'git cherry-pick --continue', then rerun --integrate."
        )

    target_commit = git_output(repo, "rev-parse", "HEAD")
    record.update(
        status="completed", integration_state="completed",
        integration_commit=agent_commit, integrated_at=now(),
        target_branch=branch, target_commit=target_commit,
        integration_parent=target_head, integration_subject=subject,
    )
    state["updated_at"] = now()
    save_state(state_path, state)



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path,
                        help="Repository workspace to operate on; orchestration code remains trusted.")
    parser.add_argument("--runs-dir", type=Path, default=Path(".agent-runs/orchestrator"))
    parser.add_argument("--resume", action="store_true", help="Resume from the existing run journal.")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--approve", metavar="TASK_ID", help="Approve a reviewed task handoff.")
    actions.add_argument("--integrate", metavar="TASK_ID", help="Integrate an approved worktree task into the current branch.")
    actions.add_argument("--cancel", metavar="TASK_ID", help="Request cooperative cancellation of a running task.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and display the DAG without creating journals or worktrees.")
    parser.add_argument("--worktrees", action="store_true", help="Run each task in its own detached Git worktree.")
    parser.add_argument(
        "--allow-unsandboxed-pi-write", action="store_true",
        help="Unsafe: explicitly authorize Pi write tasks without an OS sandbox.",
    )
    parser.add_argument(
        "--require-sandbox", action="store_true",
        help="Require OS enforcement for every Agent task; fail before execution if unavailable.",
    )
    parser.add_argument(
        "--sandbox-profile", type=Path,
        help="Trusted Sandbox Profile JSON (defaults to the stable checkout's task-developer profile).",
    )
    args = parser.parse_args()
    global ROOT
    if args.repo_root:
        ROOT = args.repo_root.resolve()
    try:
        plan = load_plan(args.plan)
        sandbox_profile = None
        sandbox_profile_sha256 = None
        if args.require_sandbox and args.allow_unsandboxed_pi_write:
            raise ValueError("--require-sandbox and --allow-unsandboxed-pi-write are mutually exclusive.")
        if args.sandbox_profile and not args.require_sandbox:
            raise ValueError("--sandbox-profile requires --require-sandbox.")
        if args.require_sandbox:
            if not args.worktrees:
                raise ValueError("--require-sandbox requires --worktrees so the task workspace is not the stable checkout.")
            sandbox_profile = (
                args.sandbox_profile.resolve() if args.sandbox_profile
                else CODE_ROOT / ".ai/runtime/examples/sandbox-profile.json"
            )
            from sandbox_runtime import load_profile
            _, sandbox_profile_sha256 = load_profile(sandbox_profile)
        runs_dir = args.runs_dir if args.runs_dir.is_absolute() else ROOT / args.runs_dir
        state_path = runs_dir / "orchestrator-state.json"
        if args.dry_run:
            for item in plan["tasks"]:
                dependencies = ", ".join(item.get("depends_on", [])) or "none"
                isolation = "worktree" if args.worktrees else "shared-workspace"
                print(f"READY {item['task_id']}: {item['task_file']} [{item.get('harness', 'codex')}] depends_on={dependencies} isolation={isolation}")
            return 0
        if args.resume:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if set(state.get("tasks", {})) != {item["task_id"] for item in plan["tasks"]}:
                raise ValueError("Existing journal does not match this plan's task IDs.")
            if state.get("worktrees_enabled", False) != args.worktrees:
                raise ValueError("Resume must use the same --worktrees setting as the original run.")
            if state.get("sandbox_required", False) != args.require_sandbox:
                raise ValueError("Resume must preserve the original --require-sandbox setting.")
            if args.require_sandbox and state.get("sandbox_profile_sha256") != sandbox_profile_sha256:
                raise ValueError("Resume must use the exact same Sandbox Profile digest as the original run.")
        else:
            if state_path.exists():
                raise ValueError(f"Run journal already exists: {state_path}; use --resume or choose another --runs-dir.")
            state = initial_state(
                plan, args.worktrees, args.require_sandbox,
                str(sandbox_profile) if sandbox_profile else None,
                sandbox_profile_sha256,
            )
            save_state(state_path, state)
        if args.approve:
            if not args.resume:
                raise ValueError("--approve requires --resume.")
            approve(args.approve, state, state_path)
            next_status = state["tasks"][args.approve]["status"]
            print(f"{args.approve}: {next_status} (human-approved)")
            return 0
        if args.integrate:
            if not args.resume or not args.worktrees:
                raise ValueError("--integrate requires both --resume and --worktrees.")
            integrate_task(ROOT, args.integrate, state, state_path)
            print(f"{args.integrate}: {state['tasks'][args.integrate]['status']} (integration)")
            return 0
        if args.cancel:
            if not args.resume:
                raise ValueError("--cancel requires --resume.")
            marker = request_cancel(args.cancel, state, runs_dir)
            print(f"{args.cancel}: cancellation requested; runner confirmation is pending ({marker})")
            return 0
        return run_plan(
            plan, runs_dir, state, args.worktrees,
            allow_unsandboxed_pi_write=args.allow_unsandboxed_pi_write,
            require_sandbox=args.require_sandbox,
            sandbox_profile=sandbox_profile,
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"agent-orchestrate: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
