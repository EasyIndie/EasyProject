# API 文档

> **🔌 API 设计概览。详细信息见各 `specs/<feature>/api.md` 和 `architecture/api.md`。**

---

## API 设计原则

- **RESTful**：资源导向的 URL 设计
- **JSON**：请求和响应体使用 JSON
- **JWT 认证**：通过 Bearer Token 认证
- **分页**：列表接口默认分页

---

## 基础 URL

```
开发环境: http://localhost:8080/api/v1
预发布: https://staging-api.example.com/api/v1
生产: https://api.example.com/api/v1
```

---

## 认证

```
Authorization: Bearer <token>
```

---

## 通用状态码

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数有误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## API 列表

（根据项目实际情况填充）

| 方法 | 路径 | 说明 | 功能 |
|------|------|------|------|
| GET | /health | 健康检查 | - |

---

## 详细标准

参见 [`docs/standards/api.md`](standards/api.md) 了解 API 设计规范。
参见 [`architecture/api.md`](../architecture/api.md) 了解 API 架构设计。
