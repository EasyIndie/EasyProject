#!/usr/bin/env python3
"""Run a self-evolution task in a candidate EasyProject worktree.

The stable checkout only creates and controls the candidate. Agent execution,
approval, and integration happen inside the candidate checkout using that
candidate's own runtime. This is orchestration, not an OS security sandbox.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
HARNESS_BINARIES = {"codex": "codex", "claude-code": "claude"}
CHECK_IDS = (
    "python-unittest", "repo-validation",
)


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
    validate_run_id(run_id)
    parent = ROOT.parent / f".{ROOT.name}-evolution"
    candidate = parent / run_id
    branch = f"evolution/{run_id}"
    return candidate, branch, candidate / ".agent-runs" / "evolution" / run_id


def make_task(run_id: str, goal: str, harness: str,
              acceptance: list[str]) -> dict:
    if not goal.strip():
        raise ValueError("goal must not be empty")
    if harness not in HARNESS_BINARIES:
        raise ValueError(f"unsupported harness: {harness}")
    if not acceptance or any(item not in CHECK_IDS for item in acceptance):
        raise ValueError("acceptance checks must include only: " + ", ".join(CHECK_IDS))
    return {
        "protocol_version": "1.0",
        "task_id": run_id,
        "issue": None,
        "objective": goal.strip(),
        "context": [
            "This is a self-evolution task for EasyProject.",
            "Read AGENTS.md and the relevant .ai/runtime documentation.",
            "The candidate checkout is isolated from the stable checkout.",
        ],
        "inputs": [
            "AGENTS.md",
            ".ai/runtime/",
            "scripts/agent-orchestrate.py",
            "scripts/agent-run.py",
            "tests/",
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
            "repository_read": True,
            "repository_write": True,
            "network_access": False,
            "secret_access": False,
            "external_side_effects": False,
        },
        "preferred_role": "developer",
        "preferred_harness": harness,
        "model_hint": None,
        "timeout_minutes": 60,
        "metadata": {
            "source": "self-evolution",
            "correlation_id": run_id,
            "labels": ["easyproject", "self-evolution"],
        },
        "acceptance_checks": acceptance,
    }


def write_run_inputs(run_dir: Path, run_id: str, task: dict) -> tuple[Path, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    task_path = run_dir / "task.json"
    plan_path = run_dir / "plan.json"
    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan = {
        "protocol_version": "1.0",
        "tasks": [{
            "task_id": run_id,
            "task_file": str(task_path),
            "harness": task["preferred_harness"],
            "depends_on": [],
            "max_attempts": 2,
        }],
    }
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return task_path, plan_path


def invoke_candidate(candidate: Path, run_dir: Path, action: list[str] | None = None, resume: bool = False) -> int:
    orchestrator = candidate / "scripts" / "agent-orchestrate.py"
    plan = run_dir / "plan.json"
    if not orchestrator.is_file() or not plan.is_file():
        raise ValueError("candidate runtime or evolution plan is missing")
    command = [
        sys.executable, str(orchestrator), "--plan", str(plan),
        "--runs-dir", str(run_dir / "orchestrator"), "--worktrees",
    ]
    if action:
        command.extend(["--resume", *action.split()])
    return subprocess.run(command, cwd=candidate, check=False).returncode


def start(args: argparse.Namespace) -> int:
    run_id = validate_run_id(args.id)
    if git("status", "--porcelain=v1"):
        raise ValueError("stable checkout must be clean before starting an evolution run")
    if not git("branch", "--show-current"):
        raise ValueError("stable checkout must be on a named branch, not detached HEAD")
    if shutil.which(HARNESS_BINARIES[args.harness]) is None:
        raise ValueError(f"Agent CLI not found on PATH: {HARNESS_BINARIES[args.harness]}")
    try:
        import jsonschema  # noqa: F401
    except ImportError as exc:
        raise ValueError("install jsonschema in the active Python environment first") from exc

    candidate, branch, run_dir = candidate_paths(run_id)
    if candidate.exists():
        raise ValueError(f"candidate path already exists: {candidate}")
    if git("branch", "--list", branch):
        raise ValueError(f"candidate branch already exists: {branch}")

    base = git("rev-parse", "HEAD")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    git("worktree", "add", "-b", branch, str(candidate), base)
    try:
        task = make_task(run_id, args.goal, args.harness, args.check or ["python-unittest"])
        write_run_inputs(run_dir, run_id, task)
    except Exception:
        # Preserve the candidate worktree for inspection if setup partially failed.
        raise

    print(f"Evolution candidate: {candidate}")
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
            raise ValueError("evolution journal does not exist")
        print(json.dumps(json.loads(state_path.read_text(encoding="utf-8")),
                         ensure_ascii=False, indent=2))
        return 0
    if args.action == "resume":
        return invoke_candidate(candidate, run_dir)
    if args.action in {"approve", "integrate"}:
        task_id = args.id
        flag = "--approve" if args.action == "approve" else "--integrate"
        return invoke_candidate(candidate, run_dir, f"{flag} {task_id}")
    raise ValueError(f"unsupported action: {args.action}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="create a candidate worktree and run a real Agent")
    start_parser.add_argument("--id", required=True)
    start_parser.add_argument("--goal", required=True)
    start_parser.add_argument("--harness", choices=tuple(HARNESS_BINARIES), required=True)
    start_parser.add_argument("--check", choices=CHECK_IDS, action="append",
                              help="allowlisted acceptance check; may be repeated")

    action_parser = subparsers.add_parser("run", help="resume, inspect, approve, or integrate a candidate")
    action_parser.add_argument("--id", required=True)
    action_parser.add_argument("action", choices=("status", "resume", "approve", "integrate", "cancel"))

    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            return start(args)
        return continue_run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"evolution: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
