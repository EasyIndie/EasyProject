import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "agent-benchmark.py"
SPEC = importlib.util.spec_from_file_location("easyproject_agent_benchmark", MODULE_PATH)
benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(benchmark)


class AgentBenchmarkTests(unittest.TestCase):
    def write_run(self, root, run_id, harness, status, check_status, attempts=1):
        runtime = root / run_id / "runtime"
        orchestrator = runtime / "orchestrator"
        orchestrator.mkdir(parents=True)
        (runtime / "manifest.json").write_text(json.dumps({
            "run_id": run_id,
            "harness": harness,
            "created_at": "2026-11-21T10:00:00+00:00",
            "environment": {"harness_version": harness + " 1.0"},
        }), encoding="utf-8")
        (orchestrator / "orchestrator-state.json").write_text(json.dumps({
            "tasks": {
                "task-1": {
                    "status": status,
                    "attempts": attempts,
                    "first_started_at": "2026-11-21T10:00:00+00:00",
                    "finished_at": "2026-11-21T10:00:30+00:00",
                    "last_exit_code": 0 if status == "awaiting_review" else 1,
                    "automated_checks": {"status": check_status},
                }
            }
        }), encoding="utf-8")

    def test_aggregates_success_checks_attempts_and_duration_by_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_run(root, "codex-a", "codex", "awaiting_review", "passed", 1)
            self.write_run(root, "codex-b", "codex", "failed", "failed", 2)
            report = benchmark.build_benchmark(root)
            codex = report["metrics_by_harness"]["codex"]
            self.assertEqual(report["run_count"], 2)
            self.assertEqual(codex["attempted_tasks"], 2)
            self.assertEqual(codex["agent_success_count"], 1)
            self.assertEqual(codex["agent_success_rate"], 0.5)
            self.assertEqual(codex["acceptance_pass_rate"], 0.5)
            self.assertEqual(codex["total_attempts"], 3)
            self.assertEqual(codex["mean_duration_seconds"], 30.0)
            self.assertIsNone(codex["token_usage"])
            self.assertIsNone(codex["estimated_cost"])

    def test_ignores_directories_without_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "unrelated").mkdir()
            report = benchmark.build_benchmark(Path(tmp))
            self.assertEqual(report["run_count"], 0)
            self.assertEqual(report["metrics_by_harness"], {})

    def test_incomplete_run_has_no_fabricated_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "partial" / "runtime"
            runtime.mkdir(parents=True)
            (runtime / "manifest.json").write_text(json.dumps({
                "run_id": "partial", "harness": "claude-code"
            }), encoding="utf-8")
            report = benchmark.build_benchmark(root)
            self.assertEqual(report["run_count"], 1)
            claude = report["metrics_by_harness"]["claude-code"]
            self.assertEqual(claude["runs"], 1)
            self.assertEqual(claude["attempted_tasks"], 0)
            self.assertIsNone(claude["mean_duration_seconds"])
            self.assertIsNone(claude["agent_success_rate"])
            self.assertIsNone(claude["acceptance_pass_rate"])


if __name__ == "__main__":
    unittest.main()
