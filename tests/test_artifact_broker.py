#!/usr/bin/env python3
"""Security tests for immutable Agent artifact exchange."""
from __future__ import annotations

import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("artifact_broker", ROOT / "scripts/artifact_broker.py")
broker = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
import sys
sys.modules["artifact_broker"] = broker
SPEC.loader.exec_module(broker)


class ArtifactBrokerTests(unittest.TestCase):
    def make_writable(self, root: Path) -> None:
        for current, directories, files in os.walk(root, topdown=False):
            current_path = Path(current)
            for name in files:
                path = current_path / name
                if not path.is_symlink():
                    os.chmod(path, 0o600)
            for name in directories:
                path = current_path / name
                if not path.is_symlink():
                    os.chmod(path, 0o700)
            os.chmod(current_path, 0o700)

    def make_workspace(self, root: Path) -> Path:
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "src").mkdir()
        (workspace / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (workspace / "report.json").write_text('{"status":"passed"}\n', encoding="utf-8")
        return workspace

    def test_export_verify_and_materialize_read_only_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.addCleanup(self.make_writable, root)
            workspace = self.make_workspace(root)
            store = root / "artifact-store"
            result = broker.export_artifact(
                workspace, store, "task-01", "test-report",
                ["src/main.py", "report.json"], "abcdef0123456789",
            )
            artifact_dir = Path(result["artifact_dir"])
            manifest = broker.verify_artifact(artifact_dir)
            self.assertEqual(manifest["artifact_id"], result["manifest"]["artifact_id"])
            self.assertEqual(len(manifest["files"]), 2)
            self.assertFalse(os.access(artifact_dir / "report.json", os.W_OK))
            destination = root / "reviewer-snapshot"
            materialized = broker.materialize_artifact(artifact_dir, destination)
            self.assertTrue(materialized["read_only"])
            self.assertEqual((destination / "src" / "main.py").read_text(), "print('hello')\n")
            self.assertFalse(os.access(destination / "src" / "main.py", os.W_OK))

    def test_export_is_content_addressed_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = self.make_workspace(root)
            store = root / "store"
            first = broker.export_artifact(workspace, store, "task-01", "diff", ["src/main.py"])
            second = broker.export_artifact(workspace, store, "task-01", "diff", ["src/main.py"])
            self.assertEqual(first["artifact_dir"], second["artifact_dir"])
            self.assertEqual(len(list(store.glob("sha256-*"))), 1)

    def test_path_traversal_and_absolute_paths_are_rejected(self):
        for path in ("../outside.txt", "/etc/passwd", "C:/Windows/win.ini", "src/../../x", "src\\secret.txt"):
            with self.subTest(path=path), self.assertRaises(broker.ArtifactError):
                broker.normalize_relative_path(path)

    def test_sensitive_paths_are_never_exported(self):
        for path in (".env", ".env.production", ".ssh/id_ed25519", ".aws/credentials", "build/signing.p12"):
            with self.subTest(path=path), self.assertRaises(broker.ArtifactError):
                broker.normalize_relative_path(path)

    def test_symlink_file_and_parent_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = self.make_workspace(root)
            outside = root / "outside.txt"
            outside.write_text("secret", encoding="utf-8")
            (workspace / "link.txt").symlink_to(outside)
            (workspace / "linked-dir").symlink_to(outside.parent, target_is_directory=True)
            with self.assertRaises(broker.ArtifactError):
                broker.export_artifact(workspace, root / "store", "task-01", "diff", ["link.txt"])
            with self.assertRaises(broker.ArtifactError):
                broker.export_artifact(workspace, root / "store", "task-01", "diff", ["linked-dir/outside.txt"])

    def test_hard_links_and_special_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = self.make_workspace(root)
            outside = root / "outside-hardlink.txt"
            os.link(workspace / "report.json", outside)
            with self.assertRaises(broker.ArtifactError):
                broker.export_artifact(workspace, root / "store", "task-01", "diff", ["report.json"])
            fifo = workspace / "pipe"
            os.mkfifo(fifo)
            with self.assertRaises(broker.ArtifactError):
                broker.export_artifact(workspace, root / "store", "task-01", "diff", ["pipe"])

    def test_oversized_files_and_total_size_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = self.make_workspace(root)
            large = workspace / "large.bin"
            large.write_bytes(b"x" * (broker.MAX_FILE_BYTES + 1))
            with self.assertRaises(broker.ArtifactError):
                broker.export_artifact(workspace, root / "store", "task-01", "diff", ["large.bin"])

    def test_store_must_be_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = self.make_workspace(root)
            with self.assertRaises(broker.ArtifactError):
                broker.export_artifact(workspace, workspace / ".artifacts", "task-01", "diff", ["report.json"])

    def test_tampered_and_undeclared_artifact_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = self.make_workspace(root)
            result = broker.export_artifact(workspace, root / "store", "task-01", "diff", ["report.json"])
            artifact_dir = Path(result["artifact_dir"])
            report = artifact_dir / "report.json"
            os.chmod(report, stat.S_IWUSR | stat.S_IRUSR)
            report.write_text("tampered", encoding="utf-8")
            with self.assertRaises(broker.ArtifactError):
                broker.verify_artifact(artifact_dir)
            os.chmod(report, stat.S_IRUSR)
            extra = artifact_dir / "extra.txt"
            os.chmod(artifact_dir, 0o755)
            extra.write_text("undeclared", encoding="utf-8")
            os.chmod(extra, 0o444)
            os.chmod(artifact_dir, 0o555)
            with self.assertRaises(broker.ArtifactError):
                broker.verify_artifact(artifact_dir)

    def test_artifact_directory_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.addCleanup(self.make_writable, root)
            workspace = self.make_workspace(root)
            result = broker.export_artifact(workspace, root / "store", "task-01", "diff", ["report.json"])
            artifact_dir = Path(result["artifact_dir"])
            alias = root / "artifact-alias"
            alias.symlink_to(artifact_dir, target_is_directory=True)
            with self.assertRaises(broker.ArtifactError):
                broker.verify_artifact(alias)

    def test_existing_materialization_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = self.make_workspace(root)
            result = broker.export_artifact(workspace, root / "store", "task-01", "diff", ["report.json"])
            destination = root / "existing"
            destination.mkdir()
            with self.assertRaises(broker.ArtifactError):
                broker.materialize_artifact(Path(result["artifact_dir"]), destination)

    def test_duplicate_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = self.make_workspace(root)
            with self.assertRaises(broker.ArtifactError):
                broker.export_artifact(workspace, root / "store", "task-01", "diff",
                                       ["report.json", "report.json"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
