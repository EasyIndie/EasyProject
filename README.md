# PROJECT_NAME

> PROJECT_DESCRIPTION

<br>

**AI Native Engineering Standard（AI 原生工程标准）** — 这不是一个代码模板，而是一套**工程规范模板**。

任何新项目从此仓库创建后，立即拥有统一的目录结构、开发流程、Agent 协作规范和文档标准。任何 AI Agent（Claude Code、Codex、OpenHands、Pi Agent 等）都能在几秒内理解项目并参与开发。

---

## 快速开始

```bash
# 1. 从本模板创建新项目
#    GitHub → "Use this template" → 填写项目信息 → Clone

# 2. 运行启动脚本
bash bootstrap.sh

# 3. AI Agent 从 .ai/ 开始
#    告诉你的 AI 工具: "阅读 .ai/README.md"
```

---

## 架构概览

本项目按照**六层职责（Six Responsibility Layers）**组织：

```
PROJECT_NAME
│
├── .ai/                   # 🤖 AI 工作区 — Agent、提示词、工作流、规则
│   ├── agents/            #    Agent 定义（planner/architect/developer/reviewer/qa/devops）
│   ├── workflows/         #    标准化工作流（feature 全流程）
│   ├── prompts/           #    可复用提示词模板
│   ├── context/           #    项目上下文（Agent 首先读这里）
│   ├── rules/             #    Agent 必须遵守的规则
│   ├── memory/            #    持久化 Agent 记忆
│   └── templates/         #    文件模板
│
├── docs/                  # 📚 文档 — 项目文档与团队规范
│   └── standards/         #    编码/API/数据库/日志/测试/文档 标准
│
├── specs/                 # 📋 需求 — 产品需求与验收标准
│
├── architecture/          # 🏗️ 架构 — 系统设计与 ADR
│   └── adr/               #    架构决策记录
│
├── tasks/                 # 📌 任务 — Kanban 看板
│   ├── todo/              #    待办
│   ├── doing/             #    进行中
│   ├── review/            #    审查中
│   └── done/              #    已完成
│
├── apps/                  # 🚀 应用 — 可部署的应用代码
├── packages/              # 📦 包 — 共享库与模块
├── infra/                 # 🏢 基础设施 — Docker、Terraform、CI/CD
├── tests/                 # 🧪 测试 — 单元/集成/E2E/性能测试
├── scripts/               # 🔧 脚本 — 自动化脚本
│
├── examples/              # 💡 示例 — 完整功能演示
│   └── hello-feature/     #    端到端功能开发流程
│
└── .github/               # ⚙️ GitHub — Actions、Issue/PR 模板、仓库规则
```

---

## AI 工作区（`.ai/`）

这是本模板**最核心的部分**。传统项目中，AI Agent 需要扫描整个代码库才能理解项目。在本模板中：

```
AI Agent 启动流程：

  1. 读取 .ai/README.md          ← 了解 AI 工作区结构
  2. 读取 .ai/context/            ← 理解项目是什么
  3. 遵守 .ai/rules/              ← 遵守所有规则
  4. 使用 .ai/workflows/          ← 按标准流程工作
  5. 参考 .ai/agents/             ← 调用合适的 Agent
```

**关键原则：**

- **先读 Context，再写代码** — Agent 必须先理解项目，不能假设
- **规则不可违反** — `.ai/rules/` 对所有 Agent 具有约束力
- **工作流是唯一路径** — 开发功能必须遵循 `.ai/workflows/feature/`
- **每个目录都有 README** — Agent 永远不会迷路

---

## 开发工作流

```
需求 ──→ 设计 ──→ 任务 ──→ 实现 ──→ 测试 ──→ 审查 ──→ 发布

 PRD  →  ADR  → Tasks → Code  → Tests → Review → Release
 specs/  arch/  tasks/  apps/   tests/  review   deploy

每个功能遵循 .ai/workflows/feature/ 的 7 步流程
```

---

## 目录地图

| 目录 | 职责 | Agent 交互 |
|------|------|------------|
| [`.ai/`](.ai/) | AI 工作区 | **每次会话从这里开始** |
| [`docs/`](docs/) | 文档与标准 | 写代码前查阅 `docs/standards/` |
| [`specs/`](specs/) | 产品需求 | 功能从这里开始，PRD + 验收标准 |
| [`architecture/`](architecture/) | 架构设计 | 理解系统全貌，记录设计决策 |
| [`tasks/`](tasks/) | 看板任务 | 执行任务，在看板中流转 |
| [`apps/`](apps/) | 应用代码 | 实现具体功能 |
| [`packages/`](packages/) | 共享库 | 复用代码，避免重复 |
| [`infra/`](infra/) | 基础设施 | 部署与环境管理 |
| [`tests/`](tests/) | 测试 | 验证功能正确性 |
| [`scripts/`](scripts/) | 自动化脚本 | 重复操作自动化 |
| [`examples/`](examples/) | 示例演示 | 学习完整开发流程 |
| [`.github/`](.github/) | GitHub 配置 | CI/CD、Issue/PR 模板 |

---

## 功能示例

查看 [`examples/hello-feature/`](examples/hello-feature/) 了解完整的端到端开发流程：

```
01_prd.md          → 产品需求文档
02_architecture.md → 架构设计 + ADR
03_tasks.md        → 任务拆解
04_implementation.md → 实现过程
05_test.md         → 测试计划与执行
06_review.md       → 代码审查
07_merge.md        → 合并与发布
```

---

## FAQ

### 为什么叫 "AI Native" 而不是 "AI Ready"？

"AI Ready" 意味着 AI 可以使用这个项目。"AI Native" 意味着项目**为 AI 而生** — AI 是第一公民，不是后来添加的适配层。

### 这个模板适合什么项目？

任何软件项目。它是语言无关、框架无关、领域无关的。从 Web 应用到嵌入式系统，从个人项目到企业级产品。

### AI Agent 真的会读这些文件吗？

是的。Claude Code、GitHub Copilot、Codex、OpenHands 等现代 AI 工具都能读取项目文件来理解上下文。本模板确保它们读到的第一段文字就是正确的引导。

### 我需要一次把所有内容填满吗？

不需要。`bootstrap.sh` 会帮你填充项目基本信息。架构和需求文档可以在开发过程中逐步完善。但 `.ai/rules/` 和 `docs/standards/` 建议从第一天就遵守。

### 我能修改这个模板吗？

当然。这是 MIT 许可证。根据自己的团队和项目调整目录结构、规则和标准。但建议保持 `.ai/` 工作区的核心概念不变。

---

## 贡献

欢迎提交 Issue 和 PR 来改进这个模板。请确保：

- 任何改动都更新相应的 README
- 新功能遵循本模板自身的开发工作流
- 保持语言和框架无关的设计原则

---

## 许可证

MIT — 见 [LICENSE](LICENSE)
