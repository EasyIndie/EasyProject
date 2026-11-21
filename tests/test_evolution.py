import hashlib
import importlib.util
import json
import subprocess
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
            self.assertEqual(manifest["task_source"], "manual-goal")
            self.assertFalse(manifest["credential_values_recorded"])
            self.assertNotIn("api_key", json.dumps(manifest).lower())

    def make_approved_artifact(self, root):
        root.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        schema_dir = root / ".ai/runtime/schemas"
        schema_dir.mkdir(parents=True)
        schema = (evolution.ROOT / ".ai/runtime/schemas/task.schema.json").read_text(encoding="utf-8")
        (schema_dir / "task.schema.json").write_text(schema, encoding="utf-8")
        source = root / "src" / "sample.py"
        source.parent.mkdir()
        source.write_text("# TODO: fix parser\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True)
        base_sha = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        task_id = "DISC-0123456789ab"
        task = {
            "protocol_version": "1.0",
            "task_id": task_id,
            "issue": None,
            "objective": "Resolve the parser TODO.",
            "context": ["Human-approved discovery task."],
            "inputs": ["src/sample.py"],
            "constraints": ["Do not access secrets or use network access."],
            "acceptance_criteria": ["The marker is resolved.", "A regression test is added."],
            "risk": "medium",
            "permissions": {
                "repository_read": True,
                "repository_write": True,
                "network_access": False,
                "secret_access": False,
                "external_side_effects": False,
            },
            "preferred_role": "developer",
            "preferred_harness": "any",
            "model_hint": None,
            "timeout_minutes": 30,
            "metadata": {
                "source": "human-approved-discovery",
                "correlation_id": task_id,
                "labels": ["discovery", "human-approved"],
            },
            "acceptance_checks": ["python-unittest"],
        }
        wrapper = {
            "promotion_version": "1.0",
            "approved_at": "2026-11-22T00:00:00+00:00",
            "approval_note": "Reviewed and approved.",
            "approval_mode": "write-enabled",
            "evidence_verified": {
                "candidate_id": task_id,
                "path": "src/sample.py",
                "line": 1,
                "marker": "TODO",
                "file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "base_sha": base_sha,
            },
            "task": task,
        }
        artifact = root.parent / "approved-task.json"
        artifact.write_text(json.dumps(wrapper), encoding="utf-8")
        return source, artifact, task_id, wrapper

    def test_loads_verified_write_enabled_task_and_overrides_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            _, artifact, task_id, _ = self.make_approved_artifact(root)
            task, evidence = evolution.load_approved_task(artifact, task_id, "codex", root)
            self.assertEqual(task["task_id"], task_id)
            self.assertEqual(task["preferred_harness"], "codex")
            self.assertTrue(task["permissions"]["repository_write"])
            self.assertEqual(evidence["path"], "src/sample.py")

    def test_rejects_read_only_promotion_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            _, artifact, task_id, wrapper = self.make_approved_artifact(root)
            wrapper["approval_mode"] = "read-only"
            artifact.write_text(json.dumps(wrapper), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "write-enabled"):
                evolution.load_approved_task(artifact, task_id, "codex", root)

    def test_rejects_stale_source_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            source, artifact, task_id, _ = self.make_approved_artifact(root)
            source.write_text("# TODO: changed after approval\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source changed"):
                evolution.load_approved_task(artifact, task_id, "codex", root)

    def test_rejects_stale_base_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            _, artifact, task_id, _ = self.make_approved_artifact(root)
            (root / "next.py").write_text("pass\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "next.py"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "advance"], check=True)
            with self.assertRaisesRegex(ValueError, "base SHA is stale"):
                evolution.load_approved_task(artifact, task_id, "codex", root)

    def test_rejects_task_id_mismatch_and_unsafe_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            _, artifact, task_id, wrapper = self.make_approved_artifact(root)
            with self.assertRaisesRegex(ValueError, "run ID"):
                evolution.load_approved_task(artifact, "different-id", "codex", root)
            wrapper["task"]["permissions"]["network_access"] = True
            artifact.write_text(json.dumps(wrapper), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot enable network"):
                evolution.load_approved_task(artifact, task_id, "codex", root)

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

    def test_plan_rejects_task_id_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = evolution.make_task(
                "different", "Add a regression test", "codex", ["python-unittest"]
            )
            with self.assertRaisesRegex(ValueError, "must match"):
                evolution.write_run_inputs(Path(tmp) / "runtime", "expected", task)


if __name__ == "__main__":
    unittest.main()
