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
