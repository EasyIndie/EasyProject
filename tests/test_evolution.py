import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "evolution.py"
SPEC = importlib.util.spec_from_file_location("easyproject_evolution", MODULE_PATH)
evolution = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evolution)


class EvolutionContractTests(unittest.TestCase):
    def test_run_id_is_restricted_to_safe_path_characters(self):
        self.assertEqual(evolution.validate_run_id("m35-first-run"), "m35-first-run")
        for invalid in ("../escape", "with space", "", "a" * 49):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    evolution.validate_run_id(invalid)

    def test_task_defaults_to_least_privilege(self):
        task = evolution.make_task(
            "m35-test", "Add a regression test", "codex", ["python-unittest"]
        )
        self.assertFalse(task["permissions"]["network_access"])
        self.assertFalse(task["permissions"]["secret_access"])
        self.assertFalse(task["permissions"]["external_side_effects"])
        self.assertTrue(task["permissions"]["repository_write"])
        self.assertEqual(task["acceptance_checks"], ["python-unittest"])

    def test_task_rejects_unallowlisted_checks(self):
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            evolution.make_task(
                "m35-test", "Add a regression test", "codex", ["arbitrary-shell"]
            )

    def test_candidate_and_runtime_data_are_siblings_outside_stable_checkout(self):
        candidate, branch, run_dir = evolution.candidate_paths("isolation-test")
        self.assertEqual(branch, "evolution/isolation-test")
        self.assertEqual(candidate.parent, run_dir.parent)
        self.assertEqual(candidate.name, "candidate")
        self.assertEqual(run_dir.name, "runtime")
        self.assertNotEqual(candidate, run_dir)
        self.assertFalse(run_dir.is_relative_to(evolution.ROOT))
        self.assertFalse(candidate.is_relative_to(evolution.ROOT))

    def test_manifest_records_reproducible_baseline_without_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "runtime"
            environment = {
                "branch": "main",
                "head": "abc123",
                "python": "3.12.1",
                "jsonschema": "4.25.1",
                "harness_version": "codex 1.2.3",
            }
            path = evolution.write_manifest(
                run_dir, "manifest-test", "Verify evidence", "codex",
                ["python-unittest"], environment,
            )
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["stable"]["base_sha"], "abc123")
            self.assertEqual(manifest["candidate"]["branch"], "evolution/manifest-test")
            self.assertFalse(manifest["credential_values_recorded"])
            self.assertNotIn("api_key", json.dumps(manifest).lower())

    def test_report_distinguishes_not_started_from_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "runtime"
            run_dir.mkdir()
            (run_dir / "manifest.json").write_text(
                json.dumps({"run_id": "report-test"}), encoding="utf-8"
            )
            report = evolution.build_report(run_dir)
            self.assertEqual(report["execution"]["status"], "not_started")
            orchestrator_dir = run_dir / "orchestrator"
            orchestrator_dir.mkdir()
            (orchestrator_dir / "orchestrator-state.json").write_text(
                json.dumps({
                    "updated_at": "2026-11-21T00:00:00Z",
                    "tasks": {
                        "task-a": {
                            "status": "awaiting_review",
                            "attempts": 1,
                            "automated_checks": {"status": "passed"},
                            "handoff": None,
                            "review_evidence": None,
                        }
                    },
                }), encoding="utf-8"
            )
            report = evolution.build_report(run_dir)
            self.assertEqual(report["execution"]["status"], "recorded")
            self.assertEqual(report["execution"]["tasks"]["task-a"]["status"], "awaiting_review")
            self.assertEqual(report["execution"]["tasks"]["task-a"]["automated_checks"], "passed")

    def test_report_requires_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "manifest not found"):
                evolution.build_report(Path(tmp))

    def test_plan_and_task_are_written_only_to_external_runtime_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "runtime"
            task = evolution.make_task(
                "case", "Add a regression test", "codex", ["python-unittest"]
            )
            task_path, plan_path = evolution.write_run_inputs(run_dir, "case", task)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(Path(plan["tasks"][0]["task_file"]), task_path)
            self.assertTrue(task_path.is_file())
            self.assertTrue(plan_path.is_file())
            self.assertEqual(task_path.parent, run_dir)


if __name__ == "__main__":
    unittest.main()
