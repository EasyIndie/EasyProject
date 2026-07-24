# 架构（Architecture）

> **🏗️ 系统设计与架构决策记录。决定"怎么做"。**

---

## 这是什么？

`architecture/` 存放系统架构设计文档和架构决策记录（ADR）。这里描述系统的拓扑结构、数据模型、API 设计、领域模型和安全策略。需求说"做什么"，这里说"怎么做"。

---

## 目录结构

```
architecture/
├── README.md              ← 你在这里
├── system.md               系统拓扑与组件设计
├── database.md             数据模型与迁移策略
├── api.md                  API 设计（认证、限流、版本）
├── ddd.md                  领域驱动设计（限界上下文、聚合）
├── security.md             安全策略（威胁模型、密钥管理）
└── adr/                    架构决策记录（Architecture Decision Records）
    ├── README.md              ADR 说明与索引
    └── 0001-template.md       ADR 模板
```

---

## 放什么？

- **系统设计** — 组件图、数据流、外部依赖、部署拓扑
- **数据模型** — ER 图、关键表结构、迁移策略
- **API 设计** — 整体 API 架构、认证/鉴权流程
- **安全策略** — 威胁模型、安全原则、密钥管理方案
- **ADR** — 重要的架构决策及其上下文、结论和后果

## 不放什么？

- **产品需求** → 放在 [`specs/`](../specs/)
- **API 具体文档** → 放在 [`docs/api.md`](../docs/api.md)
- **部署步骤** → 放在 [`docs/deployment.md`](../docs/deployment.md)

---

## ADR 格式

每个 ADR 是一个带编号的 Markdown 文件：

```markdown
# ADR-0001: 决策标题

- **状态**: proposed | accepted | deprecated | superseded
- **日期**: YYYY-MM-DD
- **上下文**: 为什么需要做这个决策？
- **决策**: 我们选择了什么方案？
- **后果**: 什么变得更容易？什么变得更困难？
```

---

## AI Agent 交互指南

1. **设计新功能前**：阅读 `system.md` 了解系统全貌
2. **做重大技术决策时**：创建 ADR 记录决策
3. **设计数据模型时**：参考 `database.md` 中的模式
4. **设计 API 时**：遵循 `api.md` 中的架构约定
5. **做安全相关改动时**：务必阅读 `security.md`

---

## 相关目录

- [`.ai/context/architecture.md`](../.ai/context/architecture.md) — Agent 快速上下文
- [`.ai/templates/adr-template.md`](../.ai/templates/adr-template.md) — ADR 模板
- [`docs/standards/api.md`](../docs/standards/api.md) — API 具体标准
- [`docs/standards/database.md`](../docs/standards/database.md) — 数据库具体标准
- [`specs/`](../specs/) — 需求，架构的前一个阶段
