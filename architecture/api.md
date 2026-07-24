# API 架构

> **🔌 API 架构设计：认证、限流、版本控制。**

---

## 认证流程

```text
Client                    API Gateway              Auth Service
  │                           │                       │
  │  POST /auth/login         │                       │
  │──────────────────────────▶│                       │
  │                           │  验证凭证              │
  │                           │──────────────────────▶│
  │                           │                       │
  │                           │  JWT Token            │
  │                           │◀──────────────────────│
  │  返回 Token + Refresh     │                       │
  │◀──────────────────────────│                       │
  │                           │                       │
  │  GET /api/users (Bearer)  │                       │
  │──────────────────────────▶│                       │
  │                           │  验证 JWT             │
  │                           │  注入 User Context    │
  │                           │──────────────────────▶│ (转发到业务服务)
```

---

## 认证策略

| 端点类型 | 认证方式 | Token 位置 |
|----------|----------|------------|
| 公共 API | 无 | - |
| 用户 API | JWT Bearer Token | Authorization Header |
| 服务间 API | API Key 或 mTLS | Header |

---

## 限流策略

| 端点 | 限制 | 窗口 |
|------|------|------|
| /auth/login | 5 次 | 每分钟 |
| /auth/register | 3 次 | 每分钟 |
| 普通 API | 100 次 | 每分钟 |
| 批量操作 | 10 次 | 每分钟 |

---

## API 版本控制

- URL 路径版本：`/api/v1/`, `/api/v2/`
- 旧版本和新版本并行运行
- 旧版本废弃后给予至少 3 个月的迁移窗口
- 废弃信息通过响应 Header 通知：

```
Deprecation: true
Sunset: Sat, 01 Jan 2025 00:00:00 GMT
```

---

## 相关文档

- REST/GraphQL 设计规范：`docs/standards/api.md`
- API 变更需要更新 `docs/api.md`
