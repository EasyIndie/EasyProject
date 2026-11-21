#!/usr/bin/env python3
"""End-to-end tests for the project bootstrapper."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="easyproject test ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project with spaces"
        (self.root / "scripts").mkdir(parents=True)
        shutil.copy2(SOURCE_ROOT / "scripts" / "bootstrap.py", self.root / "scripts" / "bootstrap.py")
        (self.root / "README.md").write_text(
            "# PROJECT_NAME\n\nPROJECT_DESCRIPTION\nPROJECT_LANGUAGE\nREPO_URL\n"
            "COPYRIGHT_HOLDER PROJECT_YEAR\n",
            encoding="utf-8",
        )
        (self.root / "docs").mkdir()
        (self.root / "docs" / "notes.txt").write_text("PROJECT_NAME", encoding="utf-8")

    def run_bootstrap(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / "bootstrap.py"), *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_dry_run_reports_changes_without_writing(self) -> None:
        before = (self.root / "README.md").read_text(encoding="utf-8")
        result = self.run_bootstrap("--yes", "--dry-run", "--name", "Demo", "--description", "Sample")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dry run", result.stdout)
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), before)

    def test_replacements_preserve_spaces_unicode_and_special_characters(self) -> None:
        name = "Demo & Tools $100 \\ release"
        description = "中文说明：100% ready"
        result = self.run_bootstrap(
            "--yes", "--name", name, "--description", description,
            "--language", "Swift, Rust", "--repo-url", "https://example.test/a?x=1&y=2",
            "--copyright", "A&B",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn(name, content)
        self.assertIn(description, content)
        self.assertIn("Swift, Rust", content)
        self.assertIn("https://example.test/a?x=1&y=2", content)
        self.assertIn("A&B", content)
        self.assertIn(name, (self.root / "docs" / "notes.txt").read_text(encoding="utf-8"))

    def test_second_run_is_idempotent(self) -> None:
        args = ("--yes", "--name", "Demo", "--description", "Sample")
        first = self.run_bootstrap(*args)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.run_bootstrap(*args)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("发现 0 个待更新文件", second.stdout)

    def test_non_interactive_mode_requires_name_and_description(self) -> None:
        result = self.run_bootstrap("--yes", "--name", "Demo")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--yes requires --name and --description", result.stderr)

    def test_help_does_not_modify_project(self) -> None:
        before = (self.root / "README.md").read_bytes()
        result = self.run_bootstrap("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "README.md").read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
