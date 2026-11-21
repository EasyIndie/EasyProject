#!/usr/bin/env python3
"""Aggregate comparable metrics from external EasyProject Evolution run evidence."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_ROOT = ROOT.parent / f".{ROOT.name}-evolution"
SUCCESS_STATES = {"awaiting_review", "approved", "completed"}


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def load_run(run_root: Path) -> dict[str, Any] | None:
    runtime = run_root / "runtime"
    manifest_path = runtime / "manifest.json"
    state_path = runtime / "orchestrator" / "orchestrator-state.json"
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    task_records = state.get("tasks", {})
    tasks = []
    for task_id, record in task_records.items():
        checks = record.get("automated_checks", {})
        started = parse_time(record.get("first_started_at") or record.get("started_at"))
        finished = parse_time(record.get("finished_at"))
        duration = None
        if started and finished:
            duration = max(0.0, (finished - started).total_seconds())
        tasks.append({
            "task_id": task_id,
            "status": record.get("status", "unknown"),
            "attempts": record.get("attempts", 0),
            "agent_success": record.get("status") in SUCCESS_STATES,
            "acceptance_status": checks.get("status", "not_recorded"),
            "duration_seconds": duration,
            "last_exit_code": record.get("last_exit_code"),
        })
    return {
        "run_id": manifest.get("run_id", run_root.name),
        "harness": manifest.get("harness", "unknown"),
        "harness_version": manifest.get("environment", {}).get("harness_version"),
        "model_hint": manifest.get("model_hint"),
        "created_at": manifest.get("created_at"),
        "tasks": tasks,
    }


def build_benchmark(runs_root: Path) -> dict[str, Any]:
    runs = []
    if runs_root.is_dir():
        for child in sorted(runs_root.iterdir()):
            if child.is_dir():
                run = load_run(child)
                if run is not None:
                    runs.append(run)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        grouped[run["harness"]].append(run)

    by_harness = {}
    for harness, harness_runs in sorted(grouped.items()):
        tasks = [task for run in harness_runs for task in run["tasks"]]
        attempted = [task for task in tasks if task["attempts"] > 0]
        successful = [task for task in attempted if task["agent_success"]]
        checks = [task for task in attempted if task["acceptance_status"] in {"passed", "failed"}]
        passed_checks = [task for task in checks if task["acceptance_status"] == "passed"]
        durations = [task["duration_seconds"] for task in attempted if task["duration_seconds"] is not None]
        by_harness[harness] = {
            "runs": len(harness_runs),
            "tasks": len(tasks),
            "attempted_tasks": len(attempted),
            "agent_success_count": len(successful),
            "agent_success_rate": len(successful) / len(attempted) if attempted else None,
            "acceptance_checked_count": len(checks),
            "acceptance_pass_rate": len(passed_checks) / len(checks) if checks else None,
            "total_attempts": sum(task["attempts"] for task in attempted),
            "mean_duration_seconds": mean(durations) if durations else None,
            "token_usage": None,
            "estimated_cost": None,
            "cost_note": "Not available in the current runner evidence; do not infer from CLI output.",
        }

    return {
        "benchmark_version": "1.0",
        "runs_root": str(runs_root),
        "run_count": len(runs),
        "comparison_warning": (
            "Compare harnesses only on equivalent task sets, repository base SHAs, "
            "acceptance checks, and comparable model/configuration settings."
        ),
        "metrics_by_harness": by_harness,
        "runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--output", type=Path, help="Write JSON to a file instead of stdout")
    args = parser.parse_args()
    try:
        result = build_benchmark(args.runs_root)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"agent-benchmark: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
