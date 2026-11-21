#!/usr/bin/env python3
"""Fail if generated self-evolution runtime artifacts are tracked by Git."""
from __future__ import annotations

import subprocess
import sys
from pathlib import PurePosixPath


FORBIDDEN_ROOTS = {
    ".agent-runs",
    ".EasyProject-evolution",
    ".evolution",
    "evolution-runs",
}


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "-z"], text=False, capture_output=True, check=False
    )
    if result.returncode:
        print(result.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        return result.returncode
    tracked = [
        item.decode("utf-8", errors="replace")
        for item in result.stdout.split(b"\0") if item
    ]
    leaked = [
        path for path in tracked
        if PurePosixPath(path).parts and PurePosixPath(path).parts[0] in FORBIDDEN_ROOTS
    ]
    if leaked:
        print("Template contains tracked runtime artifacts:", file=sys.stderr)
        for path in leaked:
            print(f"  {path}", file=sys.stderr)
        return 1
    print("Template cleanliness: no tracked Evolution runtime artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
