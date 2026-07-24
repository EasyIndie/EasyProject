# 常见问题（FAQ）

---

## 如何使用这个模板？

```bash
# 1. GitHub → "Use this template" → 创建仓库
# 2. Clone 仓库
# 3. 运行 bash bootstrap.sh
# 4. AI Agent 从 .ai/README.md 开始
```

---

## 如何添加新功能？

遵循 `.ai/workflows/feature/` 的 7 步流程：

1. 在 `specs/<feature>/` 创建 PRD
2. 在 `architecture/` 设计、必要时创建 ADR
3. 在 `tasks/todo/` 创建任务
4. 实现、测试、审查
5. 合并和发布

---

## AI Agent 如何开始工作？

告诉 AI Agent：

> "阅读 .ai/README.md 并按照指引开始工作。"

Agent 会自动：
1. 读取 `.ai/context/` 理解项目
2. 遵守 `.ai/rules/` 中的规则
3. 使用 `.ai/workflows/` 执行标准流程

---

## 我能否修改模板中的标准？

当然。`docs/standards/` 和 `.ai/rules/` 中的所有文件都可以根据你的团队需求修改。但建议：

- 所有修改通过 PR 进行
- 更新相关 README
- 如果是重大变更，创建 ADR 记录

---

## 模板适合什么类型的项目？

任何类型的软件项目。模板完全语言无关、框架无关、领域无关。

---

## 我不需要某个目录，可以删除吗？

可以。但建议保留 `.ai/`、`docs/standards/`、`.github/` 的核心结构 — 这些是 AI Native 工程标准的基础。

---

## 如何让 AI Agent 遵守规则？

`.ai/rules/` 中的规则是所有 Agent 的约束。告诉 Agent "遵守 .ai/rules/ 中的所有规则"即可。现代 AI 工具（Claude Code、GitHub Copilot 等）都能读取和理解这些 Markdown 规则文件。
