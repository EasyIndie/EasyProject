# 分支规则

> **📜 分支的创建、开发、合并和删除规范。**

---

## 分支策略

采用 **Trunk-Based Development** 的变体：

```
main (受保护)
  │
  ├── feature/xxx  (短期分支，1-3 天)
  ├── fix/xxx      (短期分支，几小时到 1 天)
  ├── docs/xxx     (短期分支)
  ├── refactor/xxx (短期分支)
  └── chore/xxx    (短期分支)
```

---

## 分支命名详解

### `feature/` — 新功能

```
feature/user-login
feature/payment-integration
feature/notification-system
```

规则：
- 从 `main` 最新提交创建
- 存活时间：1-3 天
- 完成后 Squash Merge 到 `main`

### `fix/` — Bug 修复

```
fix/token-expiry-crash
fix/mobile-layout-overlap
```

规则：
- 从 `main` 创建（除非修复的是 feature 分支上的功能）
- 存活时间：几小时到 1 天
- 如果 Bug 已在生产环境，修复后需要 hotfix 流程

### `docs/` — 文档

```
docs/api-authentication
docs/deployment-guide
```

### `refactor/` — 重构

```
refactor/user-service-split
refactor/database-connection-pool
```

规则：
- 重构**不改变**外部行为
- 如果有行为变更，那是 `feature/` 或 `fix/`

### `chore/` — 杂项

```
chore/update-node-version
chore/upgrade-dependencies
```

---

## 冲突解决

当分支与 `main` 有冲突时：

```bash
# 1. 获取最新 main
git fetch origin main

# 2. 在 feature 分支上 rebase（不是 merge）
git checkout feature/xxx
git rebase origin/main

# 3. 如果有冲突
#    - 逐个解决冲突文件
#    - git add <resolved-files>
#    - git rebase --continue

# 4. 强制推送（feature 分支允许 force push）
git push --force-with-lease origin feature/xxx
```

**注意**：
- ✅ feature/fix 分支可以 force push
- ❌ `main`/`master` 绝对不能 force push
- ✅ 使用 `--force-with-lease` 而不是 `--force`

---

## 分支清理

合并后立即删除分支：

```bash
# 删除本地分支
git branch -d feature/xxx

# 删除远程分支
git push origin --delete feature/xxx
```

---

## AI Agent 特别提示

- **开始工作前**：从最新的 `main` 创建分支
- **命名不确定时**：选择最接近的前缀（feature/fix/docs/refactor/chore）
- **分支存活期限**：如果超过 3 天还没合并，考虑是否范围太大需要拆分
- **不要在一个分支上做两件事**：如果一个分支做了"修复 Bug + 重构 + 新功能"，拆成三个
