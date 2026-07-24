# 提示词模板（Prompt Templates）

> **💬 可复用的提示词模板。AI Agent 在执行特定任务时使用。**

---

## 这是什么？

`prompts/` 存放可以被 AI Agent 直接使用的提示词模板。每个模板定义了一个常见任务的输入、输出和约束。

---

## 使用方式

1. 找到对应任务的提示词模板
2. 将模板中的占位符替换为实际内容
3. 发送给 AI Agent 执行

---

## 提示词列表

| 文件 | 用途 |
|------|------|
| `code-review.md` | 审查代码 |
| `generate-tests.md` | 生成测试 |
| `write-docs.md` | 编写文档 |
| `refactor.md` | 重构代码 |
