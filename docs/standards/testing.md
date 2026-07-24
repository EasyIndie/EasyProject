# 测试标准

> **📏 测试编写、组织和执行规范。**

---

## 测试金字塔

```text
           ╱\
          ╱  ╲  E2E        ← 少量（~10%），验证关键用户流程
         ╱────╲
        ╱      ╲  Integration  ← 中等（~30%），验证模块间交互
       ╱────────╲
      ╱          ╲  Unit       ← 大量（~60%），验证单个函数/方法
     ╱────────────╲
```

| 类型 | 速度 | 范围 | 数量 | 目的 |
|------|------|------|------|------|
| Unit | 毫秒 | 单个函数 | 最多 | 验证逻辑正确性 |
| Integration | 秒 | 跨模块 | 中等 | 验证协作正确性 |
| E2E | 分钟 | 全系统 | 最少 | 验证用户体验 |

---

## 测试命名

### 格式

```
test_<被测函数>_<场景>_<预期结果>()
should<ExpectedResult>When<Condition>()
```

### 示例

```python
# Python
def test_login_with_valid_credentials_returns_token():
def test_login_with_wrong_password_returns_401():
def test_login_with_locked_account_returns_403():
```

```typescript
// TypeScript
it('should return JWT token when credentials are valid')
it('should return 401 when password is wrong')
it('should return 403 when account is locked')
```

---

## 测试结构

遵循 **AAA 模式**：Arrange → Act → Assert

```typescript
it('should return user when ID exists', async () => {
  // Arrange — 准备测试数据和环境
  const user = await createTestUser({ id: '1', name: 'John' });

  // Act — 执行被测试的操作
  const result = await userService.getUser('1');

  // Assert — 验证结果
  expect(result.name).toBe('John');
  expect(result.id).toBe('1');
});
```

---

## 必须测试的场景

### 1. 正常路径（Happy Path）

最常见的正常使用场景。

### 2. 边界条件（Edge Cases）

- 空输入（`null`、`undefined`、`""`、`[]`、`{}`）
- 极值（`0`、`-1`、`Number.MAX_VALUE`）
- 列表边界（空列表、单元素、极大列表）
- 字符串边界（空字符串、超长字符串、特殊字符）

### 3. 异常情况（Error Cases）

- 无效输入
- 依赖失败（数据库断开、网络超时、第三方 API 错误）
- 权限不足
- 并发冲突

---

## Mock 与 Stub

### 要 Mock 的

- 外部 API 调用（网络请求）
- 数据库操作（单元测试中）
- 文件系统操作
- 时间相关的函数（`Date.now()`）

### 不要 Mock 的

- 被测试的函数本身
- 简单的数据结构
- 标准库的基本函数

---

## 覆盖率

| 指标 | 最低要求 | 建议目标 |
|------|----------|----------|
| 行覆盖率 | 70% | 80% |
| 分支覆盖率 | 60% | 75% |
| 函数覆盖率 | 80% | 90% |

覆盖率不达标不是阻塞 PR 的硬性理由，但需要在 Review 中说明原因。

---

## CI 中的测试

- **每次 Push 运行单元测试**（必须通过才能合并）
- **每次 PR 运行集成测试**（必须通过才能合并）
- **每日定时运行 E2E 测试**（主干分支）
- **失败的测试必须修复**：不要因为"偶尔失败"就跳过
