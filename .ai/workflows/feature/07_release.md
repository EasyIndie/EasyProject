# 步骤 7：发布

> **🚀 合并后的收尾工作。更新文档、打标签、部署、关闭任务。**

---

## 目标

确保代码从 "merged" 到 "done" 的所有收尾工作都完成。PR 合并不是终点，功能上线才是。

---

## 操作步骤

### 1. 更新版本

如果项目使用语义化版本：

```bash
# 根据变更类型选择
# feat → minor 版本号 +1
# fix  → patch 版本号 +1
# BREAKING CHANGE → major 版本号 +1
```

### 2. 更新变更日志

在 CHANGELOG.md（或对应文件）中记录：

```markdown
## [v1.2.0] - YYYY-MM-DD

### Added
- 用户登录接口（POST /api/auth/login）
- 用户注册接口（POST /api/auth/register）

### Changed
- ...

### Fixed
- ...
```

### 3. 打标签

```bash
git tag -a v1.2.0 -m "feat: 添加用户认证模块"
git push origin v1.2.0
```

### 4. 部署（如果 CD 未自动触发）

检查部署流程：

```
□ 是否已自动部署到开发环境？
□ 是否已自动部署到预发布环境？
□ 生产部署需要手动触发吗？
```

参考 `docs/deployment.md`。

### 5. 移动任务

将已完成的任务从 `tasks/review/` 移动到 `tasks/done/`。

### 6. 删除分支

```bash
git branch -d feature/xxx           # 删除本地分支
git push origin --delete feature/xxx # 删除远程分支
```

### 7. 验证上线

上线后验证：

```
□ 新功能在生产环境正常工作
□ 监控指标正常
□ 错误日志没有异常增多
□ 用户反馈无问题
```

### 8. 关闭相关 Issue

如果功能关联了 Issue：

- 在 Issue 中评论功能已上线
- 关闭 Issue

### 9. 更新文档

确认所有文档都已更新并合并：

```
□ specs/<feature>/ 标记为完成
□ docs/api.md 更新（如果有 API 变更）
□ docs/faq.md 更新（如果用户常问的问题）
□ .ai/context/tech-stack.md 更新（如果有技术栈变更）
```

---

## 输出

```markdown
# 发布确认：[功能名称] vX.Y.Z

## 版本
- 版本号: v1.2.0
- 标签: git tag v1.2.0

## 变更日志
（CHANGELOG 条目）

## 部署状态
| 环境 | 状态 | 验证 |
|------|------|------|
| 开发 | ✅ | 自动部署 |
| 预发布 | ✅ | 自动部署 |
| 生产 | ✅ | 手动部署，已验证 |

## 任务
| 任务 | 状态 |
|------|------|
| T001 | ✅ done |
| T002 | ✅ done |
| T003 | ✅ done |

## 后续关注
- 监控项 1: ...
- 技术债务项 1: ...
```

---

## 检查清单

```
□ 版本号已更新
□ 变更日志已更新
□ Git 标签已创建
□ 已部署到生产
□ 上线验证通过
□ 任务已移动到 done/
□ 分支已删除
□ 相关 Issue 已关闭
□ 文档已更新
```

---

## 🎉 完成！

功能开发流程结束。回到 [01_requirement.md](01_requirement.md) 开始下一个功能。
