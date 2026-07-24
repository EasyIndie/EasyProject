# 需求规格（Specifications）

> **📋 产品需求与验收标准。每个功能从这里开始。**

---

## 这是什么？

`specs/` 存放产品需求文档（PRD）、验收标准和 API 规格。**功能开发的第一步就是在这里写好需求**，然后才能进入架构设计和编码。

---

## 目录结构

```
specs/
├── README.md              ← 你在这里
├── <feature-name>/         每个功能一个子目录
│   ├── prd.md                产品需求文档
│   ├── acceptance.md         验收标准（Gherkin 风格）
│   └── api.md                API 规格（如果涉及 API 变更）
```

---

## 子目录命名规范

- 使用 kebab-case（全部小写，连字符分隔）
- 名称简洁且描述性强
- 示例：`auth/`、`payment/`、`chat/`、`notification/`

---

## 文件格式

### prd.md — 产品需求文档

```markdown
# 功能名称

## 问题（Problem）
当前用户面临什么问题？

## 目标用户（Users）
谁会使用这个功能？

## 解决方案（Solution Overview）
我们如何解决这个问题？

## 功能需求（Functional Requirements）
- FR-001: 系统必须...
- FR-002: 用户必须能够...

## 非功能需求（Non-Functional Requirements）
- 性能：响应时间 < 200ms
- 安全：需要 XX 权限
- 可用性：99.9% 在线

## 不在范围内（Out of Scope）
- 不包括 XXX

## 依赖（Dependencies）
- 依赖功能 A 完成
- 依赖第三方服务 B
```

### acceptance.md — 验收标准

使用 Gherkin 风格（Given-When-Then）：

```markdown
# 验收标准

## Scenario: 用户登录成功
- **Given** 用户已注册且账号有效
- **When** 用户输入正确的用户名和密码
- **Then** 系统返回 JWT Token
- **And** 用户被重定向到首页
```

### api.md — API 规格

```markdown
# API 规格

## POST /api/auth/login
认证用户并返回 Token。

### Request
...
### Response
...
```

---

## AI Agent 交互指南

1. **开始新功能时**：首先检查 `specs/` 中是否有对应的需求文档
2. **需求不存在时**：提示用户先编写 PRD（可使用 `.ai/templates/spec-template.md`）
3. **理解需求后**：遵循 `.ai/workflows/feature/01_requirement.md` 确认理解
4. **实现功能时**：始终参照 `acceptance.md` 中的验收标准
5. **功能完成后**：确保所有验收标准都已满足

---

## 相关目录

- [`.ai/templates/spec-template.md`](../.ai/templates/spec-template.md) — 需求文档模板
- [`.ai/workflows/feature/01_requirement.md`](../.ai/workflows/feature/01_requirement.md) — 需求理解工作流
- [`architecture/`](../architecture/) — 架构设计，需求的下一个阶段
- [`tasks/`](../tasks/) — 功能任务拆解
