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
  "tests/test_bootstrap.py"
  ".markdownlint-cli2.jsonc"
)

for file in "${required_files[@]}"; do
  if [[ ! -s "$file" ]]; then
    echo "::error file=$file::Required foundation file is missing or empty"
    exit 1
  fi
done

for tool in python3 shellcheck markdownlint-cli2 actionlint; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "::error::Required quality tool is missing: $tool"
    exit 1
  fi
done

python3 - <<'PY'
import ast
from pathlib import Path
ast.parse(Path("scripts/bootstrap.py").read_text(encoding="utf-8"))
ast.parse(Path("tests/test_bootstrap.py").read_text(encoding="utf-8"))
print("Python syntax: OK")
PY

python3 -m unittest discover --start-directory tests --pattern 'test_*.py' -v
python3 scripts/bootstrap.py --help >/dev/null
python3 scripts/bootstrap.py --yes --dry-run --name "CI Sample" --description "Bootstrap smoke test" >/dev/null

bash -n bootstrap.sh
bash -n scripts/validate-repo.sh
shellcheck bootstrap.sh scripts/validate-repo.sh

markdownlint-cli2 "**/*.md" "#node_modules" "#.git"
actionlint -color

echo "Repository quality gates: OK"
