#!/usr/bin/env python3
"""Export, verify and materialize immutable, path-safe Agent artifacts.

The broker is a trusted control-plane utility. It must run after the Agent has
stopped writing to its workspace. It does not apply patches to stable branches.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / ".ai/runtime/schemas/artifact-manifest.schema.json"
MAX_FILES = 128
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024
BLOCKED_NAMES = {
    ".git", ".hg", ".svn", ".ssh", ".aws", ".azure", ".kube", ".docker", ".netrc", ".npmrc",
    ".pypirc", ".git-credentials", ".gitconfig", ".config", ".envrc",
    "credentials", "credential", "secrets", "secret",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa", "authorized_keys",
    "credentials.json", "service-account.json", "google-credentials.json",
    "token.json", "access_token", "refresh_token", "oauth.json",
}
BLOCKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}


class ArtifactError(ValueError):
    """Artifact is invalid, unsafe, or cannot be materialized."""


def canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def safe_task_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value):
        raise ArtifactError(f"Invalid task ID: {value!r}")
    return value


def normalize_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ArtifactError("Artifact paths must be non-empty strings no longer than 1024 characters.")
    if "\x00" in value or "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ArtifactError(f"Absolute, drive-qualified, NUL, or backslash path is forbidden: {value!r}")
    raw_parts = value.split("/")
    if any(part in ("", ".", "..") for part in raw_parts):
        raise ArtifactError(f"Empty, dot, and parent path components are forbidden: {value!r}")
    path = PurePosixPath(value)
    if path.parts and path.parts[0].casefold() == "artifact.json":
        raise ArtifactError("artifact.json is reserved for the broker manifest.")
    if path.is_absolute():
        raise ArtifactError(f"Absolute artifact path is forbidden: {value!r}")
    windows_reserved = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
    for part in path.parts:
        lowered = part.lower()
        if (":" in part or part.endswith((".", " ")) or lowered in windows_reserved):
            raise ArtifactError(f"Cross-platform unsafe path component: {part!r}")
        if lowered in BLOCKED_NAMES or lowered.startswith(".env"):
            raise ArtifactError(f"Sensitive path is not exportable: {value!r}")
        if Path(part).suffix.lower() in BLOCKED_SUFFIXES | {".env"}:
            raise ArtifactError(f"Private-key or keystore file is not exportable: {value!r}")
    return path


def _regular_file_bytes(root: Path, relative: PurePosixPath) -> bytes:
    current = root
    for component in relative.parts[:-1]:
        current = current / component
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise ArtifactError(f"Cannot inspect artifact parent {relative}: {exc}") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ArtifactError(f"Artifact parent is a symlink or not a directory: {relative}")
    source = current / relative.parts[-1]
    try:
        before = os.lstat(source)
    except OSError as exc:
        raise ArtifactError(f"Cannot inspect artifact file {relative}: {exc}") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ArtifactError(f"Only regular, non-symlink files may be exported: {relative}")
    if before.st_nlink != 1:
        raise ArtifactError(f"Hard-linked files are not exportable: {relative}")
    if before.st_size > MAX_FILE_BYTES:
        raise ArtifactError(f"Artifact file exceeds {MAX_FILE_BYTES} bytes: {relative}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(source, flags)
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or opened.st_dev != before.st_dev or opened.st_ino != before.st_ino):
                raise ArtifactError(f"Artifact changed while opening: {relative}")
            content = stream.read(MAX_FILE_BYTES + 1)
            after = os.fstat(stream.fileno())
    except OSError as exc:
        raise ArtifactError(f"Cannot read artifact file {relative}: {exc}") from exc
    if (len(content) > MAX_FILE_BYTES or len(content) != before.st_size
            or after.st_size != before.st_size or after.st_mtime_ns != before.st_mtime_ns):
        raise ArtifactError(f"Artifact changed while being read or exceeded its limit: {relative}")
    return content


def _ensure_disjoint_paths(workspace: Path, store: Path) -> None:
    if workspace == store or workspace.is_relative_to(store) or store.is_relative_to(workspace):
        raise ArtifactError("Artifact store and source workspace must be disjoint directories.")


def _write_new_file(path: Path, content: bytes, mode: int = 0o444) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, mode)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, mode)


def _remove_tree(path: Path) -> None:
    if not path.exists():
        return
    for current, directories, files in os.walk(path, topdown=False, followlinks=False):
        current_path = Path(current)
        for name in files:
            child = current_path / name
            if not child.is_symlink():
                os.chmod(child, 0o600)
        for name in directories:
            child = current_path / name
            if not child.is_symlink():
                os.chmod(child, 0o700)
        os.chmod(current_path, 0o700)
    shutil.rmtree(path, ignore_errors=False)


def _make_read_only(root: Path) -> None:
    for current, directories, files in os.walk(root, topdown=False, followlinks=False):
        current_path = Path(current)
        for name in files:
            path = current_path / name
            if path.is_symlink():
                raise ArtifactError(f"Unexpected symlink in artifact staging area: {path}")
            os.chmod(path, 0o444)
        for name in directories:
            path = current_path / name
            if path.is_symlink():
                raise ArtifactError(f"Unexpected symlink in artifact staging area: {path}")
            os.chmod(path, 0o555)
    os.chmod(root, 0o555)


def export_artifact(
    workspace: Path,
    store: Path,
    task_id: str,
    kind: str,
    paths: Sequence[str],
    source_revision: str | None = None,
) -> dict:
    task_id = safe_task_id(task_id)
    if kind not in {"diff", "patch", "handoff", "test-report", "review-evidence"}:
        raise ArtifactError(f"Unsupported artifact kind: {kind}")
    if not paths or len(paths) > MAX_FILES:
        raise ArtifactError(f"Provide between 1 and {MAX_FILES} artifact paths.")
    if source_revision is not None and not re.fullmatch(r"[0-9a-f]{7,64}", source_revision):
        raise ArtifactError("source_revision must be a hexadecimal Git revision or null.")

    if workspace.is_symlink() or not workspace.is_dir():
        raise ArtifactError("Workspace must be an existing, non-symlink directory.")
    workspace = workspace.resolve()
    store = store.resolve()
    _ensure_disjoint_paths(workspace, store)
    normalized = [normalize_relative_path(item) for item in paths]
    def collision_key(item: PurePosixPath) -> str:
        return unicodedata.normalize("NFD", item.as_posix().casefold())
    collision_keys = [collision_key(item) for item in normalized]
    if len(set(collision_keys)) != len(collision_keys):
        raise ArtifactError("Case-insensitive or Unicode-normalized duplicate paths are not allowed.")
    for left in collision_keys:
        for right in collision_keys:
            if left != right and right.startswith(left.rstrip("/") + "/"):
                raise ArtifactError("Artifact paths cannot be both files and parent directories.")

    payloads: list[tuple[PurePosixPath, bytes]] = []
    total_bytes = 0
    for relative in sorted(normalized, key=lambda item: item.as_posix()):
        content = _regular_file_bytes(workspace, relative)
        total_bytes += len(content)
        if total_bytes > MAX_TOTAL_BYTES:
            raise ArtifactError(f"Artifact exceeds the {MAX_TOTAL_BYTES}-byte total size limit.")
        payloads.append((relative, content))

    files = [
        {
            "path": relative.as_posix(),
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }
        for relative, content in payloads
    ]
    manifest = {
        "protocol_version": "1.0",
        "task_id": task_id,
        "kind": kind,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "files": files,
        "total_bytes": total_bytes,
    }
    identity = {key: value for key, value in manifest.items() if key != "created_at"}
    digest = hashlib.sha256(canonical_json(identity)).hexdigest()
    manifest["artifact_id"] = f"sha256:{digest}"
    try:
        from jsonschema import Draft202012Validator, FormatChecker
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    except ImportError as exc:
        raise ArtifactError("Install jsonschema to validate artifact manifests.") from exc

    store.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".artifact-staging-", dir=store))
    try:
        for relative, content in payloads:
            target = staging.joinpath(*relative.parts)
            _write_new_file(target, content)
        _write_new_file(staging / "artifact.json", json.dumps(
            manifest, ensure_ascii=False, sort_keys=True, indent=2
        ).encode("utf-8") + b"\n")
        _make_read_only(staging)
        destination = store / f"sha256-{digest}"
        if destination.exists():
            existing_manifest = verify_artifact(destination)
            _remove_tree(staging)
            return {"artifact_dir": str(destination), "manifest": existing_manifest}
        os.replace(staging, destination)
        return {"artifact_dir": str(destination), "manifest": manifest}
    except Exception:
        try:
            _remove_tree(staging)
        except OSError:
            pass
        raise


def _read_manifest(artifact_dir: Path) -> dict:
    if artifact_dir.is_symlink() or not artifact_dir.is_dir():
        raise ArtifactError("Artifact directory must be a non-symlink directory.")
    manifest_path = artifact_dir / "artifact.json"
    try:
        manifest_info = os.lstat(manifest_path)
    except OSError as exc:
        raise ArtifactError(f"Artifact manifest is missing: {exc}") from exc
    if (stat.S_ISLNK(manifest_info.st_mode) or not stat.S_ISREG(manifest_info.st_mode)
            or manifest_info.st_nlink != 1 or manifest_info.st_size > 1024 * 1024):
        raise ArtifactError("Artifact manifest is a symlink, hard link, special file or oversized.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        from jsonschema import Draft202012Validator, FormatChecker
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"Cannot read artifact manifest: {exc}") from exc
    except ImportError as exc:
        raise ArtifactError("Install jsonschema to verify artifact manifests.") from exc
    except Exception as exc:
        raise ArtifactError(f"Artifact manifest validation failed: {exc}") from exc
    return manifest


def verify_artifact(artifact_dir: Path) -> dict:
    if artifact_dir.is_symlink():
        raise ArtifactError("Artifact directory must not be a symlink.")
    artifact_dir = artifact_dir.resolve()
    manifest = _read_manifest(artifact_dir)
    artifact_id = manifest["artifact_id"]
    payload = {key: value for key, value in manifest.items()
               if key not in {"artifact_id", "created_at"}}
    digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    if artifact_id != f"sha256:{digest}" or artifact_dir.name != f"sha256-{digest}":
        raise ArtifactError("Artifact ID does not match the canonical manifest digest.")

    expected: set[str] = set()
    for item in manifest["files"]:
        relative = normalize_relative_path(item["path"])
        path = artifact_dir.joinpath(*relative.parts)
        content = _regular_file_bytes(artifact_dir, relative)
        if len(content) != item["size_bytes"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise ArtifactError(f"Artifact content digest or size mismatch: {item['path']}")
        expected.add(relative.as_posix())

    actual: set[str] = set()
    actual_directories: set[str] = set()
    for current, directories, files in os.walk(artifact_dir, followlinks=False):
        current_path = Path(current)
        for name in directories:
            path = current_path / name
            if path.is_symlink():
                raise ArtifactError("Artifact contains a symlink directory.")
            actual_directories.add(path.relative_to(artifact_dir).as_posix())
        for name in files:
            path = current_path / name
            if path.is_symlink() or not path.is_file():
                raise ArtifactError("Artifact contains a symlink or special file.")
            relative = path.relative_to(artifact_dir).as_posix()
            if relative != "artifact.json":
                actual.add(relative)
    all_expected_directories: set[str] = set()
    for item in expected:
        parent = PurePosixPath(item).parent
        while parent.as_posix() != ".":
            all_expected_directories.add(parent.as_posix())
            parent = parent.parent
    if actual != expected or actual_directories != all_expected_directories:
        raise ArtifactError("Artifact contains missing or undeclared files/directories.")
    return manifest


def materialize_artifact(artifact_dir: Path, destination: Path) -> dict:
    manifest = verify_artifact(artifact_dir)
    if destination.exists() or destination.is_symlink():
        raise ArtifactError("Materialization destination must not already exist.")
    artifact_root = artifact_dir.resolve()
    store_root = artifact_root.parent
    destination_parent = destination.parent.resolve()
    if destination_parent == store_root or destination_parent.is_relative_to(store_root):
        raise ArtifactError("Reviewer snapshot cannot be created inside the immutable artifact store.")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ArtifactError("Materialization parent must be an existing, non-symlink directory.")
    destination.mkdir(mode=0o700)
    try:
        for item in manifest["files"]:
            relative = normalize_relative_path(item["path"])
            content = _regular_file_bytes(artifact_dir, relative)
            _write_new_file(destination.joinpath(*relative.parts), content, 0o444)
        _write_new_file(
            destination / "artifact.json",
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
            0o444,
        )
        _make_read_only(destination)
    except Exception:
        try:
            _remove_tree(destination)
        except OSError:
            pass
        raise
    return {"destination": str(destination), "artifact_id": manifest["artifact_id"], "read_only": True}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="Create an immutable artifact from a frozen task workspace.")
    export.add_argument("--workspace", required=True, type=Path)
    export.add_argument("--store", required=True, type=Path)
    export.add_argument("--task-id", required=True)
    export.add_argument("--kind", required=True,
                        choices=("diff", "patch", "handoff", "test-report", "review-evidence"))
    export.add_argument("--path", action="append", required=True, dest="paths")
    export.add_argument("--source-revision")
    verify = commands.add_parser("verify", help="Verify manifest, paths, file types and content digests.")
    verify.add_argument("--artifact-dir", required=True, type=Path)
    materialize = commands.add_parser("materialize", help="Create a new read-only reviewer snapshot.")
    materialize.add_argument("--artifact-dir", required=True, type=Path)
    materialize.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            result = export_artifact(
                args.workspace, args.store, args.task_id, args.kind,
                args.paths, args.source_revision,
            )
        elif args.command == "verify":
            result = {"valid": True, "manifest": verify_artifact(args.artifact_dir)}
        else:
            result = materialize_artifact(args.artifact_dir, args.destination)
    except (ArtifactError, OSError, ValueError) as exc:
        print(f"artifact-broker: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
