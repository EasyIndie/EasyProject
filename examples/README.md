# 示例（Examples）

> **💡 完整功能演示。学习端到端开发流程的最佳入口。**

---

## 这是什么？

`examples/` 存放完整的、真实的端到端功能演示。每个示例覆盖从需求到发布的完整流程，展示本项目的工程标准和 AI Agent 工作流如何使用。

---

## 目录结构

```
examples/
├── README.md              ← 你在这里
└── hello-feature/          Hello Feature — 第一个示例
    ├── README.md             示例概述
    ├── 01-prd.md             产品需求文档
    ├── 02-architecture.md    架构设计 + ADR
    ├── 03-tasks.md           任务拆解
    ├── 04-implementation.md  实现过程（叙事日志）
    ├── 05-test.md            测试计划与执行
    ├── 06-review.md          代码审查
    └── 07-merge.md           合并与发布
```

---

## 如何阅读示例

1. **按编号顺序阅读**：从 01 到 07，模拟真实开发流程
2. **关注文件间关联**：每个步骤的输入来自前一个步骤的输出
3. **对照模板结构**：见 `.ai/workflows/feature/` 中的标准流程
4. **AI Agent 视角**：想象自己是一个 Agent，按照这些文档逐步工作

---

## AI Agent 交互指南

1. **学习标准流程时**：阅读 `hello-feature/` 示例
2. **不确定某个步骤怎么做时**：参考对应编号的示例文件
3. **新功能开发时**：不要照抄示例，但要遵循相同的节奏
4. **示例是参考，不是模板**：每个项目的具体情况可能不同

---

## 相关目录

- [`.ai/workflows/feature/`](../.ai/workflows/feature/) — 标准 7 步工作流
- [`.ai/templates/`](../.ai/templates/) — 文件模板
- [`specs/`](../specs/) — 实际功能需求
- [`tasks/`](../tasks/) — 实际任务
