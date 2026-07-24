# ============================================================
# AI Native Engineering Standard — Makefile
# ============================================================
# 日常开发常用命令。所有目标都应文档化其意图和依赖。
#
# 用法: make <target>
# ============================================================

.PHONY: help setup check test lint build docs clean

# ----------------------------------------------------------
# 默认目标：显示帮助
# ----------------------------------------------------------
help:
	@echo ""
	@echo "AI Native Engineering Standard — 可用命令"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  make setup   — 初始化开发环境（如果还未运行 bootstrap）"
	@echo "  make check   — 运行所有检查（lint + format + type-check）"
	@echo "  make test    — 运行测试套件"
	@echo "  make lint    — 运行代码风格检查"
	@echo "  make build   — 构建项目"
	@echo "  make docs    — 验证/生成文档"
	@echo "  make clean   — 清理构建产物"
	@echo ""
	@echo "根据项目技术栈自定义以上命令。"
	@echo ""

# ----------------------------------------------------------
# setup — 初始化开发环境
# ----------------------------------------------------------
setup:
	@if [ ! -f .ai/context/project.md ]; then \
		echo "⚠  项目尚未初始化，运行 bootstrap.sh..."; \
		bash bootstrap.sh; \
	else \
		echo "✓ 项目已初始化"; \
	fi
	@echo "✓ 开发环境准备完成"

# ----------------------------------------------------------
# check — 运行所有检查
# ----------------------------------------------------------
check: lint test
	@echo "✓ 所有检查通过"

# ----------------------------------------------------------
# lint — 代码风格检查
# （根据项目语言取消注释对应命令）
# ----------------------------------------------------------
lint:
	@echo "▶ 运行 lint..."
	# TypeScript/JavaScript:
	# npx eslint .
	# Python:
	# ruff check .
	# Go:
	# golangci-lint run
	# Rust:
	# cargo clippy -- -D warnings
	@echo "✓ lint 完成（未配置，请在 Makefile 中配置）"

# ----------------------------------------------------------
# test — 运行测试
# （根据项目语言取消注释对应命令）
# ----------------------------------------------------------
test:
	@echo "▶ 运行测试..."
	# TypeScript/JavaScript:
	# npm test
	# Python:
	# pytest --cov
	# Go:
	# go test ./...
	# Rust:
	# cargo test
	@echo "✓ 测试完成（未配置，请在 Makefile 中配置）"

# ----------------------------------------------------------
# build — 构建项目
# （根据项目语言取消注释对应命令）
# ----------------------------------------------------------
build:
	@echo "▶ 构建项目..."
	# TypeScript/JavaScript:
	# npm run build
	# Go:
	# go build ./...
	# Rust:
	# cargo build --release
	@echo "✓ 构建完成（未配置，请在 Makefile 中配置）"

# ----------------------------------------------------------
# docs — 验证/生成文档
# ----------------------------------------------------------
docs:
	@echo "▶ 检查文档..."
	# 检查关键目录是否有 README
	@for dir in .ai docs specs architecture tasks apps packages infra tests scripts examples .github; do \
		if [ -d "$$dir" ] && [ ! -f "$$dir/README.md" ]; then \
			echo "⚠  $$dir/README.md 缺失"; \
		fi; \
	done
	@echo "✓ 文档检查完成"

# ----------------------------------------------------------
# clean — 清理构建产物
# （根据项目语言取消注释对应命令）
# ----------------------------------------------------------
clean:
	@echo "▶ 清理构建产物..."
	# rm -rf dist/ build/ .next/
	# rm -rf node_modules/ __pycache__/ .venv/
	@echo "✓ 清理完成（未配置，请在 Makefile 中配置）"
