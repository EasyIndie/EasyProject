# AI 工作区（AI Workspace）

> **🤖 欢迎，AI Agent。这是你的工作区入口。每次会话从这里开始。**

---

## 这是什么？

`.ai/` 是所有 AI Agent 的协作工作区。它包含了 Agent 定义、可复用提示词、标准化工作流、项目上下文、持久化记忆、行为规则和文件模板。

---

## AI Agent 会话启动流程

每次开始新会话时，**必须按以下顺序执行**：

```
1. 读取 .ai/README.md             ← 你在这里
2. 读取 .ai/context/project.md    ← 理解项目是什么
3. 读取 .ai/context/architecture.md ← 理解系统结构
4. 读取 .ai/context/tech-stack.md ← 理解技术栈
5. 阅读 .ai/rules/ 下的所有规则    ← 知道什么能做、什么不能做
6. 根据任务类型选择工作流          ← .ai/workflows/
7. 根据需要调用合适的 Agent        ← .ai/agents/
```

---

## 子目录结构

```
.ai/
│
├── README.md              ← 你在这里
│
├── context/               ← 📖 项目上下文 — Agent 首先读这里
│   ├── project.md           项目基本信息（是什么、为谁做）
│   ├── architecture.md      系统架构概览
│   └── tech-stack.md        技术栈
│
├── agents/                ← 👥 Agent 定义 — 每种 Agent 的角色和能力
│   ├── planner/             规划者：将需求拆解为任务
│   ├── architect/           架构师：设计方案
│   ├── developer/           开发者：实现代码
│   ├── reviewer/            审查者：审查代码
│   ├── qa/                  质量保证：编写和运行测试
│   └── devops/              运维：CI/CD、部署、基础设施
│
├── workflows/             ← 🔄 标准化工作流 — 每类任务的固定流程
│   └── feature/             功能开发 7 步流程
│
├── prompts/               ← 💬 提示词模板 — 可复用的提示词
│   ├── code-review.md       代码审查提示词
│   ├── generate-tests.md    生成测试提示词
│   ├── write-docs.md        写文档提示词
│   └── refactor.md          重构提示词
│
├── rules/                 ← 📜 规则 — 所有 Agent 必须遵守
│   ├── coding.md            编码规则
│   ├── git.md               Git 规则
│   ├── review.md            审查规则
│   ├── documentation.md     文档规则
│   └── branch.md            分支规则
│
├── memory/                ← 🧠 持久化记忆 — Agent 的长期记忆
│
└── templates/             ← 📝 文件模板 — Agent 生成文件时使用
    ├── task-template.md     任务文件模板
    ├── adr-template.md      ADR 模板
    ├── spec-template.md     需求规格模板
    └── code-header.md       代码文件头模板
```

---

## 关键原则

| 原则 | 说明 |
|------|------|
| **Context First** | 写任何代码之前，先读完 `.ai/context/` |
| **Rules Always** | `.ai/rules/` 中的规则不可违反，无一例外 |
| **Workflows are Paths** | 开发功能必须走 `.ai/workflows/feature/` 的 7 步流程 |
| **Templates Everywhere** | 生成新文件时使用 `.ai/templates/` |
| **Memory Persists** | 重要决策和上下文写入 `.ai/memory/` |

---

## 相关目录

- [`.ai/context/`](context/) — Agent 首先阅读
- [`.ai/rules/`](rules/) — 必须遵守的规则
- [`.ai/workflows/`](workflows/) — 标准化工作流
- [`.ai/agents/`](agents/) — Agent 定义
- [`docs/standards/`](../docs/standards/) — 编码与工程标准
- [`architecture/`](../architecture/) — 系统架构文档
