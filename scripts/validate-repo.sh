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
  "tests/test_agent_contract.py"
  "tests/test_agent_runner.py"
  "tests/test_agent_orchestrator.py"
  "scripts/agent-orchestrate.py"
  ".ai/runtime/orchestrator/README.md"
  ".ai/runtime/examples/plan.json"
  "scripts/agent-run.py"
  ".ai/runtime/schemas/task.schema.json"
  ".ai/runtime/schemas/handoff.schema.json"
  ".markdownlint-cli2.jsonc"
)

for file in "${required_files[@]}"; do
  if [[ ! -s "$file" ]]; then
    echo "::error file=$file::Required foundation file is missing or empty"
    exit 1
  fi
done

for tool in python3 shellcheck markdownlint-cli2 actionlint lychee zizmor gitleaks; do
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
ast.parse(Path("scripts/agent-run.py").read_text(encoding="utf-8"))
ast.parse(Path("tests/test_agent_runner.py").read_text(encoding="utf-8"))
ast.parse(Path("scripts/agent-orchestrate.py").read_text(encoding="utf-8"))
ast.parse(Path("tests/test_agent_orchestrator.py").read_text(encoding="utf-8"))
print("Python syntax: OK")
PY

python3 -m unittest discover --start-directory tests --pattern 'test_*.py' -v
python3 scripts/bootstrap.py --help >/dev/null
python3 scripts/bootstrap.py --yes --dry-run --name "CI Sample" --description "Bootstrap smoke test" >/dev/null

bash -n bootstrap.sh
bash -n scripts/validate-repo.sh
shellcheck bootstrap.sh scripts/validate-repo.sh

markdownlint-cli2 "**/*.md" "#node_modules" "#.git"
lychee --offline --no-progress .
actionlint -color
zizmor --collect=workflows --min-severity medium .
gitleaks git --redact --no-banner .

echo "Repository quality and security gates: OK"
