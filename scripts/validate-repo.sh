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

for file in "${required_files[@]}"; do
  if [[ ! -s "$file" ]]; then
    echo "::error file=$file::Required foundation file is missing or empty"
    exit 1
  fi
done

python3 - <<'PY'
import ast
from pathlib import Path
ast.parse(Path("scripts/bootstrap.py").read_text(encoding="utf-8"))
print("Python bootstrap syntax: OK")
PY

python3 scripts/bootstrap.py --help >/dev/null
python3 scripts/bootstrap.py --yes --dry-run --name "CI Sample" --description "Bootstrap smoke test" >/dev/null
bash -n bootstrap.sh
bash -n scripts/validate-repo.sh
echo "Repository foundation validation: OK"
