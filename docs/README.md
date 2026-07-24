# 文档（Documentation）

> **📚 项目文档与团队工程规范。这是代码质量的"真源"（Source of Truth）。**

---

## 这是什么？

`docs/` 存放项目级文档和团队工程标准。所有 AI Agent 和开发者在编写代码前都应该查阅这里的标准。

---

## 目录结构

```
docs/
├── README.md              ← 你在这里
├── deployment.md           部署文档
├── api.md                  API 设计概览
├── faq.md                  常见问题
└── standards/              ← ⭐ 工程标准（最重要）
    ├── coding.md             编码标准
    ├── api.md                API 设计标准
    ├── database.md           数据库标准
    ├── logging.md            日志标准
    ├── testing.md            测试标准
    └── documentation.md      文档标准
```

---

## 放什么？

- **工程标准**（`standards/`）— 所有代码必须遵守的规范
- **部署文档** — 如何部署和运维
- **API 概览** — 面向外部用户的 API 说明
- **FAQ** — 团队常见问题

## 不放什么？

- **产品需求** → 放在 [`specs/`](../specs/)
- **架构设计** → 放在 [`architecture/`](../architecture/)
- **任务** → 放在 [`tasks/`](../tasks/)
- **自动生成的文档** → 应该由 CI 生成，不提交到仓库

---

## AI Agent 交互指南

1. **写代码前**：阅读 `standards/coding.md`，了解编码风格
2. **设计 API 前**：阅读 `standards/api.md`，遵循 API 约定
3. **操作数据库前**：阅读 `standards/database.md`，遵循数据库规范
4. **写测试前**：阅读 `standards/testing.md`，了解测试要求
5. **写日志前**：阅读 `standards/logging.md`，使用正确的日志格式
6. **新功能完成后**：检查 `standards/documentation.md`，确保文档更新

---

## 相关目录

- [`.ai/rules/`](../.ai/rules/) — AI Agent 行为规则
- [`architecture/`](../architecture/) — 系统架构文档
- [`specs/`](../specs/) — 产品需求文档
