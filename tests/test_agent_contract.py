#!/usr/bin/env python3
"""Validate the harness-neutral agent task and handoff JSON Schemas."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".ai" / "runtime"


class AgentContractTests(unittest.TestCase):
    def load_json(self, relative_path: str) -> dict:
        return json.loads((RUNTIME / relative_path).read_text(encoding="utf-8"))

    def test_task_schema_and_example_are_valid(self) -> None:
        schema = self.load_json("schemas/task.schema.json")
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(self.load_json("examples/task.json"))

    def test_handoff_schema_and_example_are_valid(self) -> None:
        schema = self.load_json("schemas/handoff.schema.json")
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(self.load_json("examples/handoff.json"))

    def test_task_rejects_missing_acceptance_criteria(self) -> None:
        schema = self.load_json("schemas/task.schema.json")
        task = self.load_json("examples/task.json")
        task.pop("acceptance_criteria")
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(task)

    def test_task_rejects_unknown_permission(self) -> None:
        schema = self.load_json("schemas/task.schema.json")
        task = self.load_json("examples/task.json")
        task["permissions"]["can_merge"] = True
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(task)

    def test_task_rejects_unknown_metadata_fields(self) -> None:
        schema = self.load_json("schemas/task.schema.json")
        task = self.load_json("examples/task.json")
        task["metadata"]["api_key"] = "must-not-be-accepted"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(task)


if __name__ == "__main__":
    unittest.main(verbosity=2)
