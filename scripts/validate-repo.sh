#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

required_files=(
  "AGENTS.md"
  "CLAUDE.md"
  ".github/copilot-instructions.md"
  ".ai/README.md"
  ".ai/agents/README.md"
  ".ai/workflows/README.md"
  "scripts/bootstrap.py"
)

missing=0
for file in "${required_files[@]}"; do
  if [[ ! -s "$file" ]]; then
    echo "::error file=$file::Required foundation file is missing or empty"
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

python3 - <<'PY'
from pathlib import Path
import ast

ast.parse(Path("scripts/bootstrap.py").read_text(encoding="utf-8"))
print("Python bootstrap syntax: OK")
PY

bash -n bootstrap.sh
bash -n scripts/validate-repo.sh
echo "Repository foundation validation: OK"
