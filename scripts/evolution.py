#!/usr/bin/env python3
"""Run a self-evolution task with all mutable run data outside the repository."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
HARNESS_BINARIES = {"codex": "codex", "claude-code": "claude"}
CHECK_IDS = ("python-unittest", "pytest", "swift-test", "cargo-test", "npm-test", "go-test", "repo-validation")


def git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def validate_run_id(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,47}", value):
        raise ValueError("run ID must be 1-48 characters: letters, digits, dot, underscore, hyphen")
    return value


def candidate_paths(run_id: str) -> tuple[Path, str, Path]:
    """Return candidate worktree, branch, and external mutable runtime directory."""
    validate_run_id(run_id)
    run_root = ROOT.parent / f".{ROOT.name}-evolution" / run_id
    candidate = run_root / "candidate"
    branch = f"evolution/{run_id}"
    run_dir = run_root / "runtime"
    return candidate, branch, run_dir


def preflight(harness: str) -> dict:
    """Inspect local prerequisites without reading credentials or invoking an Agent."""
    if harness not in HARNESS_BINARIES:
        raise ValueError(f"unsupported harness: {harness}")
    if git("rev-parse", "--is-inside-work-tree") != "true":
        raise ValueError("current directory is not a Git worktree")
    branch = git("branch", "--show-current")
    if not branch:
        raise ValueError("stable checkout must be on a named branch, not detached HEAD")
    if git("status", "--porcelain=v1"):
        raise ValueError("stable checkout must be clean before starting an evolution run")
    binary = HARNESS_BINARIES[harness]
    executable = shutil.which(binary)
    if executable is None:
        raise ValueError(f"Agent CLI not found on PATH: {binary}")
    try:
        import jsonschema
        jsonschema_version = getattr(jsonschema, "__version__", "installed")
    except ImportError as exc:
        raise ValueError("install jsonschema in the active Python environment first") from exc
    version = subprocess.run(
        [executable, "--version"], text=True, capture_output=True,
        check=False, timeout=10,
    )
    if version.returncode:
        raise ValueError(f"{binary} --version failed: {version.stderr.strip()}")
    return {
        "status": "ready",
        "repository": str(ROOT),
        "branch": branch,
        "head": git("rev-parse", "HEAD"),
        "working_tree": "clean",
        "python": platform.python_version(),
        "jsonschema": jsonschema_version,
        "harness": harness,
        "harness_executable": executable,
        "harness_version": (version.stdout or version.stderr).strip(),
    }


def write_manifest(run_dir: Path, run_id: str, goal: str,
                   harness: str, checks: list[str], preflight_result: dict,
                   task_source: str = "manual-goal", task_id: str | None = None,
                   approval_evidence: dict | None = None) -> Path:
    manifest = {
        "manifest_version": "1.0",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "goal": goal.strip(),
        "task_id": task_id or run_id,
        "task_source": task_source,
        "approval_evidence": approval_evidence,
        "harness": harness,
        "acceptance_checks": checks,
        "stable": {
            "repository": str(ROOT),
            "branch": preflight_result["branch"],
            "base_sha": preflight_result["head"],
        },
        "candidate": {
            "branch": f"evolution/{run_id}",
            "path": str(candidate_paths(run_id)[0]),
        },
        "runtime_directory": str(run_dir),
        "environment": {
            "python": preflight_result["python"],
            "jsonschema": preflight_result["jsonschema"],
            "harness_version": preflight_result["harness_version"],
        },
        "credential_values_recorded": False,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_report(run_dir: Path) -> dict:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Evolution manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    state_path = run_dir / "orchestrator" / "orchestrator-state.json"
    if not state_path.is_file():
        return {"manifest": manifest, "execution": {"status": "not_started", "tasks": {}}}
    state = json.loads(state_path.read_text(encoding="utf-8"))
    tasks = {}
    for task_id, record in state.get("tasks", {}).items():
        checks = record.get("automated_checks", {})
        tasks[task_id] = {
            "status": record.get("status", "unknown"),
            "attempts": record.get("attempts", 0),
            "automated_checks": checks.get("status", "not_recorded"),
            "handoff_exists": bool(record.get("handoff") and Path(record["handoff"]).is_file()),
            "review_evidence_exists": bool(
                record.get("review_evidence") and Path(record["review_evidence"]).is_file()
            ),
            "termination_reason": record.get("termination_reason"),
        }
    return {
        "manifest": manifest,
        "execution": {
            "status": "recorded",
            "updated_at": state.get("updated_at"),
            "tasks": tasks,
        },
    }


def make_task(run_id: str, goal: str, harness: str,
              acceptance: list[str]) -> dict:
    if not goal.strip():
        raise ValueError("goal must not be empty")
    if harness not in HARNESS_BINARIES:
        raise ValueError(f"unsupported harness: {harness}")
    if not acceptance or any(item not in CHECK_IDS for item in acceptance):
        raise ValueError("allowlisted acceptance checks must include only: " + ", ".join(CHECK_IDS))
    if len(acceptance) != len(set(acceptance)):
        raise ValueError("acceptance checks must be unique")
    return {
        "protocol_version": "1.0",
        "task_id": run_id,
        "issue": None,
        "objective": goal.strip(),
        "context": [
            "This is a self-evolution task for EasyProject.",
            "Read AGENTS.md and the relevant .ai/runtime documentation.",
            "The candidate checkout is isolated from the stable checkout.",
            "All mutable task inputs, logs, journals, and evidence live outside the repository.",
        ],
        "inputs": [
            "AGENTS.md", ".ai/runtime/", "scripts/agent-orchestrate.py",
            "scripts/agent-run.py", "tests/",
        ],
        "constraints": [
            "Make the smallest coherent change that satisfies the objective.",
            "Do not access secrets or credential stores.",
            "Do not enable network access or perform external side effects.",
            "Do not modify GitHub security settings, publish, deploy, push, or merge.",
            "Do not weaken existing tests, permission checks, or human approval gates.",
            "Report exact commands and outcomes; never claim unrun checks passed.",
        ],
        "acceptance_criteria": [
            "The requested change is implemented with focused regression coverage.",
            "Existing behavior and security boundaries remain intact.",
            "All configured acceptance checks pass in the isolated task worktree.",
        ],
        "risk": "medium",
        "permissions": {
            "repository_read": True, "repository_write": True,
            "network_access": False, "secret_access": False,
            "external_side_effects": False,
        },
        "preferred_role": "developer",
        "preferred_harness": harness,
        "model_hint": None,
        "timeout_minutes": 60,
        "metadata": {
            "source": "self-evolution", "correlation_id": run_id,
            "labels": ["easyproject", "self-evolution"],
        },
        "acceptance_checks": acceptance,
    }


def load_approved_task(task_file: Path, run_id: str, harness: str,
                       root: Path = ROOT) -> tuple[dict, dict]:
    """Load a human-promoted task and revalidate its source evidence before execution."""
    root = root.resolve()
    wrapper = json.loads(task_file.read_text(encoding="utf-8"))
    if wrapper.get("promotion_version") != "1.0":
        raise ValueError("task file is not a supported human-promotion artifact")
    if wrapper.get("approval_mode") != "write-enabled":
        raise ValueError("approved task must explicitly enable repository writes")
    if not wrapper.get("approval_note"):
        raise ValueError("approved task is missing its approval note")

    evidence = wrapper.get("evidence_verified", {})
    if evidence.get("candidate_id") != run_id:
        raise ValueError("approved task candidate ID does not match the Evolution run ID")
    current_sha = git("rev-parse", "HEAD", cwd=root)
    if evidence.get("base_sha") != current_sha:
        raise ValueError("approved task base SHA is stale; rediscover and approve again")
    relative = evidence.get("path")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("approved task evidence path is invalid")
    if ".." in Path(relative).parts:
        raise ValueError("approved task evidence path must not traverse outside the repository")
    source = root / relative
    if source.is_symlink():
        raise ValueError("approved task evidence path must not be a symlink")
    resolved = source.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("approved task evidence path escapes the repository") from exc
    git("ls-files", "--error-unmatch", "--", relative, cwd=root)
    raw = resolved.read_bytes()
    if hashlib.sha256(raw).hexdigest() != evidence.get("file_sha256"):
        raise ValueError("approved task source changed after approval")
    lines = raw.decode("utf-8").splitlines()
    line_number = evidence.get("line")
    marker = evidence.get("marker")
    if not isinstance(line_number, int) or line_number < 1 or line_number > len(lines):
        raise ValueError("approved task evidence line is invalid")
    if marker not in {"TODO", "FIXME", "HACK"} or not re.search(
        rf"(?<![A-Za-z0-9_]){re.escape(marker)}(?![A-Za-z0-9_])",
        lines[line_number - 1],
    ):
        raise ValueError("approved task marker no longer exists at the recorded location")

    task = wrapper.get("task")
    if not isinstance(task, dict) or task.get("task_id") != run_id:
        raise ValueError("Evolution run ID must exactly match the approved Task Envelope ID")
    permissions = task.get("permissions", {})
    if not permissions.get("repository_read") or not permissions.get("repository_write"):
        raise ValueError("approved task must explicitly allow repository read and write")
    if any(permissions.get(key) for key in (
        "network_access", "secret_access", "external_side_effects"
    )):
        raise ValueError("approved task cannot enable network, secrets, or external side effects")
    task["preferred_harness"] = harness
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise ValueError("jsonschema is required to validate the approved task") from exc
    schema_path = root / ".ai/runtime/schemas/task.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(task)
    return task, {
        "path": relative,
        "line": line_number,
        "marker": marker,
        "file_sha256": evidence["file_sha256"],
        "base_sha": current_sha,
    }


def write_run_inputs(run_dir: Path, run_id: str, task: dict) -> tuple[Path, Path]:
    if task.get("task_id") != run_id:
        raise ValueError("run ID must match the Task Envelope task_id")
    run_dir.mkdir(parents=True, exist_ok=True)
    task_path = run_dir / "task.json"
    plan_path = run_dir / "plan.json"
    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan = {
        "protocol_version": "1.0",
        "tasks": [{
            "task_id": run_id, "task_file": str(task_path),
            "harness": task["preferred_harness"], "depends_on": [], "max_attempts": 2,
        }],
    }
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return task_path, plan_path


def invoke_candidate(candidate: Path, run_dir: Path,
                     action: list[str] | None = None, resume: bool = False) -> int:
    orchestrator = candidate / "scripts" / "agent-orchestrate.py"
    plan = run_dir / "plan.json"
    if not orchestrator.is_file() or not plan.is_file():
        raise ValueError("candidate runtime or external evolution plan is missing")
    command = [
        sys.executable, str(orchestrator), "--plan", str(plan),
        "--runs-dir", str(run_dir / "orchestrator"), "--worktrees",
    ]
    if resume:
        command.append("--resume")
    if action:
        command.extend(action)
    return subprocess.run(command, cwd=candidate, check=False).returncode


def start(args: argparse.Namespace) -> int:
    run_id = validate_run_id(args.id)
    if git("status", "--porcelain=v1"):
        raise ValueError("stable checkout must be clean before starting an evolution run")

    approval_evidence = None
    if args.approved_task:
        task, approval_evidence = load_approved_task(args.approved_task, run_id, args.harness)
        goal = task["objective"]
        checks = args.check if args.check is not None else (
            task.get("acceptance_checks") or ["python-unittest"]
        )
        if len(checks) != len(set(checks)):
            raise ValueError("acceptance checks must be unique")
        task["acceptance_checks"] = checks
        from jsonschema import Draft202012Validator
        schema = json.loads((ROOT / ".ai/runtime/schemas/task.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(task)
        task_source = "human-approved-discovery"
    else:
        goal = args.goal
        checks = args.check or ["python-unittest"]
        task = make_task(run_id, goal, args.harness, checks)
        task_source = "manual-goal"

    environment = preflight(args.harness)
    candidate, branch, run_dir = candidate_paths(run_id)
    run_root = candidate.parent
    if run_root.exists():
        raise ValueError(f"evolution run directory already exists: {run_root}")
    if git("branch", "--list", branch):
        raise ValueError(f"candidate branch already exists: {branch}")

    base = git("rev-parse", "HEAD")
    run_root.mkdir(parents=True)
    try:
        git("worktree", "add", "-b", branch, str(candidate), base)
        write_run_inputs(run_dir, run_id, task)
        write_manifest(
            run_dir, run_id, goal, args.harness, checks, environment,
            task_source=task_source, task_id=task["task_id"],
            approval_evidence=approval_evidence,
        )
    except Exception:
        # Keep partial state for diagnosis; never silently delete a worktree or evidence.
        raise

    print(f"Evolution candidate: {candidate}")
    print(f"Evolution runtime data (outside repository): {run_dir}")
    print(f"Evolution branch: {branch}")
    print(f"Stable base: {base}")
    print("Starting the candidate's own orchestrator with isolated task worktrees.")
    return invoke_candidate(candidate, run_dir)


def continue_run(args: argparse.Namespace) -> int:
    candidate, _, run_dir = candidate_paths(args.id)
    if not candidate.is_dir():
        raise ValueError(f"candidate worktree does not exist: {candidate}")
    if args.action == "status":
        state_path = run_dir / "orchestrator" / "orchestrator-state.json"
        if not state_path.is_file():
            raise ValueError("evolution journal does not exist in the external runtime directory")
        print(json.dumps(json.loads(state_path.read_text(encoding="utf-8")),
                         ensure_ascii=False, indent=2))
        return 0
    if args.action == "resume":
        return invoke_candidate(candidate, run_dir, resume=True)
    if args.action in {"approve", "integrate", "cancel"}:
        flag = {"approve": "--approve", "integrate": "--integrate", "cancel": "--cancel"}[args.action]
        return invoke_candidate(candidate, run_dir, action=[flag, args.id], resume=True)
    raise ValueError(f"unsupported action: {args.action}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start_parser = subparsers.add_parser("start", help="create a candidate worktree and run a real Agent")
    start_parser.add_argument("--id", required=True)
    source_group = start_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--goal", help="create a new generic self-evolution task")
    source_group.add_argument("--approved-task", type=Path,
                              help="execute a write-enabled artifact from agent-task-approve.py")
    start_parser.add_argument("--harness", choices=tuple(HARNESS_BINARIES), required=True)
    start_parser.add_argument("--check", choices=CHECK_IDS, action="append",
                              help="override task acceptance checks with allowlisted IDs")
    doctor_parser = subparsers.add_parser("doctor", help="check local prerequisites without starting an Agent")
    doctor_parser.add_argument("--harness", choices=tuple(HARNESS_BINARIES), required=True)
    report_parser = subparsers.add_parser("report", help="print the evidence-backed report for a run")
    report_parser.add_argument("--id", required=True)
    action_parser = subparsers.add_parser("run", help="resume, inspect, approve, or integrate a candidate")
    action_parser.add_argument("--id", required=True)
    action_parser.add_argument("action", choices=("status", "resume", "approve", "integrate", "cancel"))
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            return start(args)
        if args.command == "doctor":
            print(json.dumps(preflight(args.harness), ensure_ascii=False, indent=2))
            return 0
        if args.command == "report":
            _, _, run_dir = candidate_paths(args.id)
            print(json.dumps(build_report(run_dir), ensure_ascii=False, indent=2))
            return 0
        return continue_run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"evolution: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
