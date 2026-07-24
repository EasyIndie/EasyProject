# 任务看板（Tasks）

> **📌 Kanban 看板。任务的完整生命周期：todo → doing → review → done。**

---

## 这是什么？

`tasks/` 是项目的看板（Kanban）。所有功能实现都以任务（Task）的形式存在，Agent 将任务在各列之间流转。

---

## 目录结构

```
tasks/
├── README.md              ← 你在这里
├── todo/                   待办 — 尚未开始的任务
├── doing/                  进行中 — 正在实现的任务
├── review/                 审查中 — 等待 Review 的任务
└── done/                   已完成 — 已合并的任务
```

---

## 任务文件命名

- 格式：`NNNN-short-name.md`（NNNN 为 4 位序号，从 0001 开始）
- 示例：`0001-add-health-check.md`

---

## 任务文件格式

每个任务文件遵循统一格式（模板见 `.ai/templates/task-template.md`）：

```markdown
# T0001: 任务标题

## 目标（Goal）
一句话描述这个任务要达成什么。

## 背景（Background）
为什么需要做这个任务？关联哪个功能或 Issue？

## 涉及文件（Files）
- path/to/file1.py — 修改 XXX
- path/to/file2.py — 新增 YYY

## 实施计划（Plan）
1. 步骤 1: ...
2. 步骤 2: ...
3. 步骤 3: ...

## 检查清单（Checklist）
- [ ] 代码符合 coding 标准
- [ ] 测试已添加
- [ ] 文档已更新
- [ ] 验收标准已满足

## 验收标准（Acceptance）
- Given XXX, When YYY, Then ZZZ
- 性能要求、安全要求等

## 结果（Result）
（任务完成后填写）
- 实际做了什么
- 遇到的问题
- 学到的东西
```

---

## 任务流转规则

```
                    ┌──────────┐
                    │   todo   │  ← 新任务创建在这里
                    └────┬─────┘
                         │ Agent 认领任务
                    ┌────▼─────┐
                    │  doing   │  ← 正在实现
                    └────┬─────┘
                         │ 实现完成、自测通过
                    ┌────▼─────┐
                    │  review  │  ← 等待 Review / PR 已开
                    └────┬─────┘
                         │ PR 已合并
                    ┌────▼─────┐
                    │   done   │  ← 功能已发布
                    └──────────┘
```

---

## AI Agent 交互指南

1. **开始工作前**：检查 `doing/` 是否有未完成的任务（不要重复工作）
2. **认领任务**：将文件从 `todo/` 移动到 `doing/`
3. **实现过程中**：更新 `doing/` 中任务的检查清单
4. **实现完成后**：将文件从 `doing/` 移动到 `review/`，填写 Result
5. **PR 合并后**：将文件从 `review/` 移动到 `done/`
6. **文件名不要变**：只在目录间移动，保持文件名不变

---

## 相关目录

- [`.ai/templates/task-template.md`](../.ai/templates/task-template.md) — 任务文件模板
- [`.ai/workflows/feature/03_tasks.md`](../.ai/workflows/feature/03_tasks.md) — 任务拆解流程
- [`.ai/workflows/feature/04_implementation.md`](../.ai/workflows/feature/04_implementation.md) — 任务实现流程
- [`specs/`](../specs/) — 需求，任务的来源
