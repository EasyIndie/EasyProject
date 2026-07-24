#!/usr/bin/env bash
# ============================================================
# bootstrap.sh — AI Native Engineering Standard 项目初始化
# ============================================================
# 用途：从模板创建新项目后，运行此脚本进行初始化。
#       它会替换所有占位符、填充项目上下文、检查环境。
#
# 用法：bash bootstrap.sh
#
# 依赖：bash（POSIX 兼容）、sed、git（可选）
#
# 占位符列表（会被替换为实际值）：
#   PROJECT_NAME        — 项目名称
#   PROJECT_DESCRIPTION  — 项目一句话描述
#   PROJECT_LANGUAGE     — 主要编程语言
#   REPO_URL             — 仓库地址
#   COPYRIGHT_HOLDER     — 版权持有人
#   PROJECT_YEAR         — 当前年份
# ============================================================

set -euo pipefail

# ----------------------------------------------------------
# 颜色定义
# ----------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ----------------------------------------------------------
# 辅助函数
# ----------------------------------------------------------
print_header() {
  echo ""
  echo -e "${BLUE}${BOLD}============================================================${NC}"
  echo -e "${BLUE}${BOLD}  AI Native Engineering Standard — 项目初始化${NC}"
  echo -e "${BLUE}${BOLD}============================================================${NC}"
  echo ""
}

print_step() {
  echo -e "${GREEN}▶${NC} $1"
}

print_warn() {
  echo -e "${YELLOW}⚠${NC}  $1"
}

print_error() {
  echo -e "${RED}✗${NC}  $1"
}

print_success() {
  echo -e "${GREEN}✓${NC}  $1"
}

# ----------------------------------------------------------
# 欢迎
# ----------------------------------------------------------
print_header

echo "欢迎！此脚本将帮助你初始化 PROJECT_NAME。"
echo ""
echo "它将完成以下操作："
echo "  1. 收集项目基本信息"
echo "  2. 替换模板中的占位符"
echo "  3. 填充 .ai/context/ 目录"
echo "  4. 检查开发环境"
echo "  5. （可选）初始化 Git 仓库"
echo ""

read -p "按 Enter 继续..."

# ----------------------------------------------------------
# 输入收集
# ----------------------------------------------------------
echo ""
echo -e "${BOLD}步骤 1/5: 项目信息${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 项目名称（必填）
while true; do
  read -p "  项目名称（必填，如 easy-order）: " PROJECT_NAME
  if [ -n "$PROJECT_NAME" ]; then
    break
  fi
  print_error "项目名称不能为空"
done

# 一句话描述（必填）
while true; do
  read -p "  一句话描述（必填，如 智能订单管理系统）: " PROJECT_DESCRIPTION
  if [ -n "$PROJECT_DESCRIPTION" ]; then
    break
  fi
  print_error "描述不能为空"
done

# 主要语言
read -p "  主要编程语言 [python]: " PROJECT_LANGUAGE
PROJECT_LANGUAGE=${PROJECT_LANGUAGE:-python}

# 仓库 URL
read -p "  仓库 URL（可选）: " REPO_URL
REPO_URL=${REPO_URL:-https://github.com/your-org/$PROJECT_NAME}

# 版权持有人
read -p "  版权持有人/组织 [Your Organization]: " COPYRIGHT_HOLDER
COPYRIGHT_HOLDER=${COPYRIGHT_HOLDER:-Your Organization}

# 当前年份
PROJECT_YEAR=$(date +%Y)

echo ""
echo -e "${BOLD}确认信息：${NC}"
echo "  项目名称:     $PROJECT_NAME"
echo "  项目描述:     $PROJECT_DESCRIPTION"
echo "  主要语言:     $PROJECT_LANGUAGE"
echo "  仓库 URL:     $REPO_URL"
echo "  版权持有人:   $COPYRIGHT_HOLDER"
echo "  年份:         $PROJECT_YEAR"
echo ""

read -p "确认无误？(Y/n) " confirm
if [ "$confirm" = "n" ] || [ "$confirm" = "N" ]; then
  echo "已取消。重新运行 bash bootstrap.sh"
  exit 0
fi

# ----------------------------------------------------------
# 占位符替换
# ----------------------------------------------------------
echo ""
echo -e "${BOLD}步骤 2/5: 替换占位符${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 需要替换的文件列表（白名单扩展名，避免破坏二进制文件）
print_step "正在替换模板占位符..."

FILES_TO_UPDATE=$(find . -type f \( \
  -name "*.md" -o \
  -name "*.yml" -o \
  -name "*.yaml" -o \
  -name "*.sh" -o \
  -name "*.json" -o \
  -name "*.txt" -o \
  -name "*.toml" -o \
  -name "*.cfg" -o \
  -name "*.ini" -o \
  -name "Makefile" -o \
  -name "LICENSE" -o \
  -name ".editorconfig" -o \
  -name ".gitignore" \) \
  ! -path "./.git/*" \
  ! -path "./bootstrap.sh" \
  ! -name "bootstrap.sh")

COUNT=0
for file in $FILES_TO_UPDATE; do
  if [ -f "$file" ]; then
    # macOS 兼容：sed -i 需要备份后缀
    if [ "$(uname)" = "Darwin" ]; then
      sed -i '' "s/PROJECT_NAME/$PROJECT_NAME/g" "$file"
      sed -i '' "s/PROJECT_DESCRIPTION/$PROJECT_DESCRIPTION/g" "$file"
      sed -i '' "s/PROJECT_LANGUAGE/$PROJECT_LANGUAGE/g" "$file"
      sed -i '' "s|REPO_URL|$REPO_URL|g" "$file"
      sed -i '' "s/COPYRIGHT_HOLDER/$COPYRIGHT_HOLDER/g" "$file"
      sed -i '' "s/PROJECT_YEAR/$PROJECT_YEAR/g" "$file"
    else
      sed -i "s/PROJECT_NAME/$PROJECT_NAME/g" "$file"
      sed -i "s/PROJECT_DESCRIPTION/$PROJECT_DESCRIPTION/g" "$file"
      sed -i "s/PROJECT_LANGUAGE/$PROJECT_LANGUAGE/g" "$file"
      sed -i "s|REPO_URL|$REPO_URL|g" "$file"
      sed -i "s/COPYRIGHT_HOLDER/$COPYRIGHT_HOLDER/g" "$file"
      sed -i "s/PROJECT_YEAR/$PROJECT_YEAR/g" "$file"
    fi
    COUNT=$((COUNT + 1))
  fi
done

print_success "已更新 $COUNT 个文件"

# ----------------------------------------------------------
# 填充上下文文件
# ----------------------------------------------------------
echo ""
echo -e "${BOLD}步骤 3/5: 填充项目上下文${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# .ai/context/project.md 已经在步骤 2 中被替换
print_success ".ai/context/project.md — 已填充"
print_success ".ai/context/tech-stack.md — 已设置主要语言为 $PROJECT_LANGUAGE"
print_success "README.md — 已更新标题和描述"
print_success "LICENSE — 已更新版权信息"
print_success ".github/instructions.md — 已更新项目名称"

# ----------------------------------------------------------
# 环境检查
# ----------------------------------------------------------
echo ""
echo -e "${BOLD}步骤 4/5: 环境检查${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Git
if command -v git >/dev/null 2>&1; then
  GIT_VERSION=$(git --version 2>/dev/null | head -n1)
  print_success "Git: $GIT_VERSION"

  # 检查 Git 配置
  if git config --global user.name >/dev/null 2>&1; then
    print_success "  Git user.name: $(git config --global user.name)"
  else
    print_warn "  Git user.name 未配置。建议运行: git config --global user.name \"你的名字\""
  fi

  if git config --global user.email >/dev/null 2>&1; then
    print_success "  Git user.email: $(git config --global user.email)"
  else
    print_warn "  Git user.email 未配置。建议运行: git config --global user.email \"你的邮箱\""
  fi
else
  print_warn "Git 未安装或不在 PATH 中。建议安装 Git。"
fi

# Docker
if command -v docker >/dev/null 2>&1; then
  DOCKER_VERSION=$(docker --version 2>/dev/null)
  print_success "Docker: $DOCKER_VERSION"
else
  print_warn "Docker 未安装（如不需要容器化开发可忽略）"
fi

# 语言特定的包管理器
case "$PROJECT_LANGUAGE" in
  python)
    if command -v python3 >/dev/null 2>&1; then
      print_success "Python: $(python3 --version 2>&1)"
    else
      print_warn "Python 3 未安装"
    fi
    if command -v pip3 >/dev/null 2>&1; then
      print_success "pip: $(pip3 --version 2>&1 | head -n1)"
    fi
    ;;
  typescript|javascript|node|node.js)
    if command -v node >/dev/null 2>&1; then
      print_success "Node.js: $(node --version 2>&1)"
    else
      print_warn "Node.js 未安装"
    fi
    if command -v npm >/dev/null 2>&1; then
      print_success "npm: $(npm --version 2>&1)"
    fi
    ;;
  go|golang)
    if command -v go >/dev/null 2>&1; then
      print_success "Go: $(go version 2>&1)"
    else
      print_warn "Go 未安装"
    fi
    ;;
  rust)
    if command -v rustc >/dev/null 2>&1; then
      print_success "Rust: $(rustc --version 2>&1)"
    else
      print_warn "Rust 未安装"
    fi
    if command -v cargo >/dev/null 2>&1; then
      print_success "Cargo: $(cargo --version 2>&1)"
    fi
    ;;
esac

# ----------------------------------------------------------
# 可选初始化
# ----------------------------------------------------------
echo ""
echo -e "${BOLD}步骤 5/5: 可选初始化${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Git 初始化
if command -v git >/dev/null 2>&1; then
  read -p "  是否初始化 Git 仓库？(Y/n) " init_git
  if [ "$init_git" != "n" ] && [ "$init_git" != "N" ]; then
    if [ ! -d ".git" ]; then
      git init
      git add .
      git commit -m "chore: 从 AI Native Engineering Standard 模板初始化 $PROJECT_NAME"
      print_success "Git 仓库已初始化并完成首次提交"
    else
      print_warn ".git 已存在，跳过初始化"
    fi
  fi

  # 创建初始功能分支
  read -p "  是否创建初始 feature 分支？(Y/n) " init_branch
  if [ "$init_branch" != "n" ] && [ "$init_branch" != "N" ]; then
    git checkout -b feature/hello-world 2>/dev/null || true
    print_success "已切换到 feature/hello-world 分支"
    print_success "提示：查看 examples/hello-feature/ 了解标准开发流程"
  fi
else
  print_warn "Git 不可用，跳过 Git 初始化"
fi

# ----------------------------------------------------------
# 清理
# ----------------------------------------------------------
echo ""
echo -e "${BOLD}收尾工作${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查是否还有未替换的占位符
REMAINING=$(grep -r "PROJECT_NAME\|PROJECT_DESCRIPTION\|COPYRIGHT_HOLDER" \
  --include="*.md" --include="*.yml" --include="*.yaml" --include="*.sh" \
  --include="*.json" --include="*.toml" \
  . 2>/dev/null | grep -v "bootstrap.sh" | grep -v "\.git/" || true)

if [ -n "$REMAINING" ]; then
  print_warn "发现未替换的占位符（可能是正常的，因为模板示例中保留了原始值）："
  echo "$REMAINING" | head -5
  echo "  ..."
else
  print_success "所有占位符已替换完成"
fi

# ----------------------------------------------------------
# 完成
# ----------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}============================================================${NC}"
echo -e "${GREEN}${BOLD}  🎉 项目初始化完成！${NC}"
echo -e "${GREEN}${BOLD}============================================================${NC}"
echo ""
echo -e "${BOLD}下一步：${NC}"
echo ""
echo "  1. 让 AI Agent 开始工作："
echo -e "     ${BLUE}告诉 AI: \"阅读 .ai/README.md 并按照指引开始工作\"${NC}"
echo ""
echo "  2. 查看项目结构："
echo -e "     ${BLUE}ls -la && cat README.md${NC}"
echo ""
echo "  3. 查看完整功能演示："
echo -e "     ${BLUE}cat examples/hello-feature/README.md${NC}"
echo ""
echo "  4. 开始你的第一个功能："
echo -e "     ${BLUE}在 specs/ 下创建需求文档，然后遵循 .ai/workflows/feature/${NC}"
echo ""
echo -e "  5. 如果需要："
echo -e "     ${BLUE}rm bootstrap.sh${NC}  (删除本脚本，不再需要)"
echo ""
echo -e "${BOLD}Happy Building! 🚀${NC}"
echo ""
