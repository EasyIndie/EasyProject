# 测试（Tests）

> **🧪 测试套件。验证功能正确性，防止回归。**

---

## 这是什么？

`tests/` 存放所有测试代码。测试按类型和被测模块组织。每个 PR 的 CI 流水线都会自动运行这些测试。

---

## 目录结构

```
tests/
├── README.md              ← 你在这里
├── unit/                    单元测试 — 快速、隔离
│   ├── apps/                  按应用组织
│   └── packages/              按包组织
├── integration/             集成测试 — 跨模块交互
├── e2e/                     端到端测试 — 完整用户流程
└── performance/             性能测试 — 负载、压力
```

---

## 测试原则

遵循测试金字塔：

```
           ╱\
          ╱  ╲  E2E        ← 少量，验证关键用户流程
         ╱────╲
        ╱      ╲  Integration  ← 中等数量，验证模块间交互
       ╱────────╲
      ╱          ╲  Unit       ← 大量，验证单个函数/方法
     ╱────────────╲
```

| 类型 | 速度 | 范围 | 数量 |
|------|------|------|------|
| Unit | 快（ms） | 单个函数 | 最多 |
| Integration | 中（s） | 跨模块 | 中等 |
| E2E | 慢（min） | 全系统 | 最少 |
| Performance | 慢 | 特定场景 | 按需 |

---

## 命名规范

- 文件名：`test_<module>.py` 或 `<module>.test.ts`（遵循语言惯例）
- 测试函数：`test_<what>_<expected_result>()` 或 `should<ExpectedResult>When<Condition>()`

---

## AI Agent 交互指南

1. **写新代码时**：同时编写对应的单元测试
2. **修改现有代码前**：先运行相关测试确保通过
3. **修改代码后**：确保所有测试仍然通过
4. **发现 Bug 时**：先写一个复现 Bug 的测试，再修复
5. **测试覆盖率**：参考 `docs/standards/testing.md` 中的覆盖率要求

---

## 相关目录

- [`docs/standards/testing.md`](../docs/standards/testing.md) — 测试标准
- [`.ai/prompts/generate-tests.md`](../.ai/prompts/generate-tests.md) — 生成测试提示词
- [`.ai/workflows/feature/05_testing.md`](../.ai/workflows/feature/05_testing.md) — 测试执行流程
