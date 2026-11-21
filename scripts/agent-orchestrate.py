#!/usr/bin/env python3
"""Run a dependency-aware, serial queue of local Agent Task Envelopes.

This is a lightweight local orchestrator, not a sandbox or a distributed queue.
A task is not considered complete until a human explicitly approves its handoff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/agent-run.py"
TERMINAL = {"completed", "failed", "blocked"}


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


def initial_state(plan: dict[str, Any], use_worktrees: bool = False) -> dict[str, Any]:
    return {
        "protocol_version": "1.0",
        "worktrees_enabled": use_worktrees,
        "updated_at": now(),
        "tasks": {
            item["task_id"]: {
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


def run_plan(plan: dict[str, Any], runs_dir: Path, state: dict[str, Any], use_worktrees: bool) -> int:
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
            if any(status in {"failed", "blocked"} for status in dependency_states):
                record.update(status="blocked", updated_at=now())
                state["updated_at"] = now()
                save_state(state_path, state)
                progress = True
                continue
            if any(status != "completed" for status in dependency_states):
                continue
            task_path = (ROOT / item["task_file"]).resolve()
            if not task_path.is_relative_to(ROOT):
                raise ValueError(f"{task_id}: task_file must stay inside the repository.")
            attempt = record["attempts"] + 1
            task_output = runs_dir / task_id / f"attempt-{attempt}.handoff.json"
            task_output.parent.mkdir(parents=True, exist_ok=True)
            workspace = prepare_worktree(ROOT, runs_dir, task_id, record) if use_worktrees else ROOT
            command = [
                sys.executable, str(RUNNER), "--task", str(task_path),
                "--harness", item.get("harness", "codex"),
                "--output", str(task_output), "--cwd", str(workspace),
            ]
            record.update(status="running", attempts=attempt, updated_at=now())
            state["updated_at"] = now()
            save_state(state_path, state)
            result = subprocess.run(command, cwd=ROOT, check=False)
            record["last_exit_code"] = result.returncode
            record["handoff"] = str(task_output)
            if result.returncode == 0:
                # The adapter intentionally emits partial; only explicit human
                # approval may transition this task to completed.
                record["status"] = "awaiting_review"
            elif attempt < item.get("max_attempts", 1):
                record["status"] = "retryable"
            else:
                record["status"] = "failed"
            record["updated_at"] = now()
            state["updated_at"] = now()
            save_state(state_path, state)
            progress = True
            # Stop after one actual agent invocation: review/approval is a gate.
            print(f"{task_id}: {record['status']} (exit={result.returncode}, attempt={attempt})")
            return 1 if result.returncode else 0
    save_state(state_path, state)
    return 0


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
    if handoff.get("status") == "failed":
        raise ValueError("A failed handoff cannot be approved.")
    record.update(status="completed", approved_at=now(), updated_at=now())
    state["updated_at"] = now()
    save_state(state_path, state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--runs-dir", type=Path, default=Path(".agent-runs/orchestrator"))
    parser.add_argument("--resume", action="store_true", help="Resume from the existing run journal.")
    parser.add_argument("--approve", metavar="TASK_ID", help="Approve a reviewed task handoff.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and display the DAG without creating journals or worktrees.")
    parser.add_argument("--worktrees", action="store_true", help="Run each task in its own detached Git worktree.")
    args = parser.parse_args()
    try:
        plan = load_plan(args.plan)
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
        else:
            if state_path.exists():
                raise ValueError(f"Run journal already exists: {state_path}; use --resume or choose another --runs-dir.")
            state = initial_state(plan, args.worktrees)
            save_state(state_path, state)
        if args.approve:
            approve(args.approve, state, state_path)
            print(f"{args.approve}: completed (human-approved)")
            return 0
        return run_plan(plan, runs_dir, state, args.worktrees)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"agent-orchestrate: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
