#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: Python 3 is required to initialize this template." >&2
  exit 1
fi

exec python3 "$ROOT/scripts/bootstrap.py" "$@"
