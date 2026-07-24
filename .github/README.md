# GitHub 配置

> **⚙️ GitHub 特定配置：Actions 工作流、Issue/PR 模板、仓库规则。**

---

## 这是什么？

`.github/` 存放所有 GitHub 平台的配置文件。这些文件控制 CI/CD 行为、Issue/PR 的标准格式、代码所有权和 AI 工具可读取的仓库规则。

---

## 目录结构

```
.github/
├── README.md                      ← 你在这里
├── instructions.md                  ⭐ 仓库规则（AI 工具读取）
├── workflows/                      GitHub Actions 工作流
│   └── ci.yml                        CI 流水线骨架
├── ISSUE_TEMPLATE/                 Issue 模板
│   ├── feature_request.md           功能请求
│   └── bug_report.md                Bug 报告
├── PULL_REQUEST_TEMPLATE/          PR 模板
│   └── pull_request_template.md     PR 描述
└── CODEOWNERS                      代码所有权
```

---

## 关键文件说明

### `instructions.md`

这是**最重要的桥梁文件**。GitHub Copilot、Claude Code 等 AI 工具在分析仓库时会读取此文件。它告诉 AI：

- 项目是什么
- 必须遵守的规则在哪里（指向 `.ai/rules/`）
- 编码标准在哪里（指向 `docs/standards/`）
- Git 约定是什么

### 其他文件

- `workflows/ci.yml` — CI 流水线骨架，需要根据项目技术栈定制
- `ISSUE_TEMPLATE/` — 标准化的 Issue 模板，减少沟通成本
- `PULL_REQUEST_TEMPLATE/` — 标准化的 PR 描述模板
- `CODEOWNERS` — 定义谁拥有代码审查权

---

## AI Agent 交互指南

1. **进入仓库后**：优先读取 `instructions.md` 了解规则
2. **创建 Issue 时**：使用 ISSUE_TEMPLATE 中的模板格式
3. **创建 PR 时**：使用 PULL_REQUEST_TEMPLATE 中的模板格式
4. **修改 CI 时**：参考 `workflows/ci.yml` 的骨架结构

---

## 相关目录

- [`.ai/rules/`](../.ai/rules/) — AI Agent 行为规则
- [`docs/standards/`](../docs/standards/) — 工程标准
- [`.ai/`](../.ai/) — AI 工作区入口
