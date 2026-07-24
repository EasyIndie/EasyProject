# 应用（Apps）

> **🚀 可部署的应用代码。每个子目录是一个独立可部署单元。**

---

## 这是什么？

`apps/` 存放项目中的所有应用程序。每个应用是一个独立的可部署单元，有自己的入口点、配置和依赖。

---

## 目录结构

```
apps/
├── README.md              ← 你在这里
├── web/                     Web 前端应用
├── api/                     API 服务
├── admin/                  管理后台
├── mobile/                 移动端应用
└── worker/                 后台任务处理
```

---

## 命名规范

- 使用 kebab-case（全部小写，连字符分隔）
- 名称简洁，一眼能看出应用用途
- 示例：`web/`、`admin/`、`api/`、`landing-page/`

---

## 每个应用的标准 README 格式

```markdown
# 应用名称

## 用途（Purpose）
这个应用做什么？

## 技术栈（Tech Stack）
- 语言/框架
- 主要依赖

## 本地开发（Local Dev）
# 安装 & 运行

## 构建（Build）
# 如何构建

## 部署（Deploy）
# 如何部署

## 环境变量（Environment Variables）
| 变量名 | 说明 | 默认值 |
```

---

## 放什么？

- 可独立部署的应用代码
- 应用级的配置和 Dockerfile
- 应用级测试（或指向 `tests/` 目录）

## 不放什么？

- **多应用共享的代码** → 放在 [`packages/`](../packages/)
- **基础设施配置** → 放在 [`infra/`](../infra/)
- **通用脚本** → 放在 [`scripts/`](../scripts/)

---

## AI Agent 交互指南

1. **创建新应用时**：在子目录下创建标准 README
2. **修改应用时**：先阅读应用的 README 了解本地运行方式
3. **添加共享代码时**：先考虑是否应该放在 `packages/`
4. **应用间通信**：通过 API，不直接引用代码

---

## 相关目录

- [`packages/`](../packages/) — 共享库
- [`infra/`](../infra/) — 部署配置
- [`tests/`](../tests/) — 测试（按应用组织）
