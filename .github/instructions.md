# 仓库规则（Repository Instructions）

> **🤖 AI 工具（GitHub Copilot、Claude Code、Codex 等）：请首先阅读本文件。**

---

## 项目信息

- **项目名称**：PROJECT_NAME
- **项目描述**：PROJECT_DESCRIPTION
- **主要语言**：PROJECT_LANGUAGE
- **仓库地址**：REPO_URL

---

## AI 工作区

所有 AI 工具和 Agent 的协作规范位于 `.ai/` 目录。

**每次会话开始时的标准流程**：

1. 读取 `.ai/README.md` — 了解 AI 工作区结构
2. 读取 `.ai/context/project.md` — 理解项目
3. 读取 `.ai/context/architecture.md` — 理解系统架构
4. 读取 `.ai/context/tech-stack.md` — 了解技术栈
5. 阅读 `.ai/rules/` 下所有规则文件
6. 根据任务类型选择 `.ai/workflows/` 中的工作流

---

## 必须遵守的规则

### 编码规则 → `.ai/rules/coding.md`

- 可读性优先于聪明
- 函数短小（不超过 30 行）
- 命名清晰有意义
- 错误必须显式处理
- 不留下注释掉的代码

### Git 规则 → `.ai/rules/git.md`

- 一个功能 = 一个分支 = 一个 PR = 一次合并
- 分支命名：`feature/`、`fix/`、`docs/`、`refactor/`、`chore/`
- 提交信息遵循约定式提交：`feat:`、`fix:`、`docs:` 等
- 绝不 force push 到 `main`

### 审查规则 → `.ai/rules/review.md`

- 每个 PR 必须经过审查
- 审查对照编码、安全、测试、文档四个维度
- 反馈必须具体且可操作

### 文档规则 → `.ai/rules/documentation.md`

- 新功能必须有 PRD
- 公共 API 必须有文档注释
- 每个目录必须有 README
- 重大技术决策必须创建 ADR

### 分支规则 → `.ai/rules/branch.md`

- 从 `main` 创建短期分支
- 存活不超过 3 天
- 合并后立即删除

---

## 工程标准

编码、API、数据库、测试、日志、文档的具体标准见 `docs/standards/`。

写代码前务必查阅对应的标准文件。

---

## 工作流

开发新功能必须遵循 `.ai/workflows/feature/` 的 7 步流程：

```
01_requirement → 02_design → 03_tasks → 04_implementation
→ 05_testing → 06_review → 07_release
```

---

## 目录地图

| 目录 | 用途 |
|------|------|
| `.ai/` | AI 工作区（Agent、工作流、规则、模板） |
| `docs/` | 项目文档与工程标准 |
| `specs/` | 产品需求与验收标准 |
| `architecture/` | 系统设计与 ADR |
| `tasks/` | Kanban 看板 |
| `apps/` | 可部署应用 |
| `packages/` | 共享库 |
| `infra/` | 基础设施即代码 |
| `tests/` | 测试套件 |
| `scripts/` | 自动化脚本 |
| `examples/` | 完整功能演示 |

---

## 遇到不确定的事情？

- 设计问题 → 参考 `architecture/`
- 编码问题 → 参考 `docs/standards/coding.md`
- 流程问题 → 参考 `.ai/workflows/`
- 没有答案 → 提出问题，不要猜测
