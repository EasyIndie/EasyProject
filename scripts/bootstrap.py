#!/usr/bin/env python3
"""Safe, repeatable project-template initialization."""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path

TEXT_SUFFIXES = {
    ".md", ".yml", ".yaml", ".sh", ".json", ".txt", ".toml",
    ".cfg", ".ini", ".py", ".ts", ".js", ".html", ".css",
}
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build",
    "__pycache__", ".next", ".nuxt",
}


def ask(label: str, default: str, required: bool = False) -> str:
    while True:
        value = input(f"{label} [{default}]: ").strip() or default
        if value or not required:
            return value
        print("此项必填。")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a project created from EasyProject.")
    parser.add_argument("--name")
    parser.add_argument("--description")
    parser.add_argument("--language", help="Comma-separated stack, e.g. TypeScript, Cocos Creator, JSON")
    parser.add_argument("--repo-url")
    parser.add_argument("--copyright")
    parser.add_argument("--yes", action="store_true", help="Non-interactive; requires --name and --description.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned replacements without writing files.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    default_name = root.name
    values = {
        "PROJECT_NAME": args.name or os.getenv("PROJECT_NAME", ""),
        "PROJECT_DESCRIPTION": args.description or os.getenv("PROJECT_DESCRIPTION", ""),
        "PROJECT_LANGUAGE": args.language or os.getenv("PROJECT_LANGUAGE", "Not specified"),
        "REPO_URL": args.repo_url or os.getenv("REPO_URL", ""),
        "COPYRIGHT_HOLDER": args.copyright or os.getenv("COPYRIGHT_HOLDER", "Your Organization"),
        "PROJECT_YEAR": str(dt.date.today().year),
    }

    if args.yes:
        if not values["PROJECT_NAME"] or not values["PROJECT_DESCRIPTION"]:
            parser.error("--yes requires --name and --description (or matching environment variables).")
    else:
        print("\nEasyProject initialization\n")
        values["PROJECT_NAME"] = values["PROJECT_NAME"] or ask("项目名称", default_name, True)
        values["PROJECT_DESCRIPTION"] = values["PROJECT_DESCRIPTION"] or ask("一句话描述", "TODO: describe this project", True)
        values["PROJECT_LANGUAGE"] = values["PROJECT_LANGUAGE"] or ask("技术栈（逗号分隔）", "Not specified")
        values["REPO_URL"] = values["REPO_URL"] or ask("仓库 URL", "")
        values["COPYRIGHT_HOLDER"] = values["COPYRIGHT_HOLDER"] or ask("版权持有人", "Your Organization")
        print("\n将使用以下信息：")
        for key, value in values.items():
            print(f"  {key}: {value}")
        if input("\n确认并继续？[Y/n] ").strip().lower() in {"n", "no"}:
            print("已取消，未修改任何文件。")
            return 0

    if not values["REPO_URL"]:
        values["REPO_URL"] = f"https://github.com/your-org/{values['PROJECT_NAME']}"

    changed: list[tuple[Path, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name in {"bootstrap.py", "bootstrap.sh"}:
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.name not in {"LICENSE", "Makefile", ".gitignore", ".editorconfig"} and path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        updated = original
        for token, value in values.items():
            updated = updated.replace(token, value)
        if updated != original:
            changed.append((path, updated))

    print(f"\n发现 {len(changed)} 个待更新文件：")
    for path, _ in changed:
        print(f"  {path.relative_to(root)}")
    if args.dry_run:
        print("\nDry run：未写入任何文件。")
        return 0

    for path, content in changed:
        path.write_text(content, encoding="utf-8")
    print(f"\n初始化完成：更新了 {len(changed)} 个文件。")
    print("下一步：检查 .ai/context/，再让 Agent 阅读 AGENTS.md。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
