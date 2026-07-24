# Git 规则

> **📜 所有 AI Agent 和开发者必须遵守此 Git 规则。**

---

## 核心铁律

```
一个功能 = 一个分支 = 一个 PR = 一次合并
One Feature = One Branch = One PR = One Merge
```

**绝不**：
- ❌ 直接在 `main` / `master` 上提交
- ❌ `force push` 到 `main` / `master`
- ❌ 一个 PR 包含多个不相关的功能

---

## 分支命名规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feature/` | 新功能 | `feature/user-auth` |
| `fix/` | Bug 修复 | `fix/login-timeout` |
| `docs/` | 文档更新 | `docs/api-guide` |
| `refactor/` | 重构（不改功能） | `refactor/extract-logger` |
| `chore/` | 杂项（依赖更新、配置） | `chore/update-deps` |
| `test/` | 测试相关 | `test/add-unit-tests` |

**规则：全部小写，连字符分隔，简洁有意义**

---

## 提交信息规范

使用 **约定式提交（Conventional Commits）**：

```
<type>: <简短描述>

[可选的详细描述]
```

### Type 类型

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构（不修 Bug，不加功能） |
| `perf` | 性能优化 |
| `test` | 添加或修改测试 |
| `chore` | 构建、依赖、配置 |
| `ci` | CI/CD 变更 |

### 示例

```
feat: 添加用户登录接口

实现了基于 JWT 的用户认证，包含 Token 刷新机制。
关联: #123
```

```
fix: 修复 Token 过期后不刷新的问题

当 API 返回 401 时，现在会自动尝试刷新 Token。
关联: #456
```

---

## 分支生命周期

```
1. 从 main 创建分支
   git checkout -b feature/xxx main

2. 在分支上开发
   git add .
   git commit -m "feat: xxx"

3. 保持分支更新（rebase，不是 merge）
   git fetch origin
   git rebase origin/main

4. 推送到远程
   git push origin feature/xxx

5. 创建 PR

6. 通过审查后 Squash Merge 到 main

7. 删除分支
   git branch -d feature/xxx
```

---

## PR 要求

- **一个 PR 只做一件事**
- **PR 标题遵循约定式提交格式**
- **PR 描述必须包含**：
  - 做了什么
  - 为什么这样做
  - 关联的 Task/Issue
  - 测试情况
- **PR 必须关联 Task**：在描述中 `Closes #NNN` 或 `Refs #NNN`

---

## AI Agent 特别提示

- **每次提交前**：检查提交信息是否符合约定式提交格式
- **创建分支前**：确认分支名称符合规范
- **不要在一个 PR 中混合 feat 和 refactor**：分开提交
- **Rebase，不要 Merge**：保持 `main` 历史线性
- **如果不知道用什么 type**：优先 `chore`，然后问人
