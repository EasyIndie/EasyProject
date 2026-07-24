# API 设计标准

> **📏 REST 和 GraphQL API 设计规范。**

---

## REST API 约定

### URL 设计

```
✅ 好的 URL：
GET    /api/users              # 列表
GET    /api/users/:id          # 详情
POST   /api/users              # 创建
PUT    /api/users/:id          # 全量更新
PATCH  /api/users/:id          # 部分更新
DELETE /api/users/:id          # 删除

✅ 嵌套资源（不超过一层）：
GET    /api/users/:id/orders           # 用户的订单列表
GET    /api/users/:id/orders/:orderId  # 用户的某个订单

❌ 坏的做法：
GET    /api/getUser?id=123             # 不要在 URL 中放动词
POST   /api/users/create               # 同上
GET    /api/users/:id/orders/:orderId/items/:itemId  # 嵌套太深
```

### HTTP 方法

| 方法 | 语义 | 幂等 | 安全 |
|------|------|------|------|
| GET | 读取 | ✅ | ✅ |
| POST | 创建 | ❌ | ❌ |
| PUT | 全量替换 | ✅ | ❌ |
| PATCH | 部分更新 | ❌ | ❌ |
| DELETE | 删除 | ✅ | ❌ |

### 状态码

| 状态码 | 时机 |
|--------|------|
| 200 OK | GET/PUT/PATCH 成功 |
| 201 Created | POST 创建成功（附带 Location header） |
| 204 No Content | DELETE 成功（无响应体） |
| 400 Bad Request | 请求格式错误、参数校验失败 |
| 401 Unauthorized | 未认证（Token 无效或缺失） |
| 403 Forbidden | 已认证但无权限 |
| 404 Not Found | 资源不存在 |
| 409 Conflict | 资源冲突（如重复用户名） |
| 422 Unprocessable Entity | 参数格式正确但语义错误 |
| 429 Too Many Requests | 触发限流 |
| 500 Internal Server Error | 服务器内部错误 |

---

### 响应格式

#### 成功响应

```json
{
  "data": {
    "id": "123",
    "name": "John",
    "email": "john@example.com"
  }
}
```

#### 列表响应（带分页）

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 100,
    "totalPages": 5
  }
}
```

#### 错误响应

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [
      {
        "field": "email",
        "message": "不是有效的邮箱格式"
      }
    ]
  }
}
```

---

### 分页

使用基于页面的分页，参数：

```
GET /api/users?page=1&pageSize=20&sort=createdAt&order=desc
```

| 参数 | 默认值 | 最大值 |
|------|--------|--------|
| page | 1 | - |
| pageSize | 20 | 100 |
| sort | createdAt | 字段白名单 |
| order | desc | asc / desc |

---

### 版本控制

在 URL 中包含版本号：

```
GET /api/v1/users
GET /api/v2/users
```

新的大版本 API 与旧版本并行运行，给予迁移窗口期。

---

### 认证

```
Authorization: Bearer <JWT_TOKEN>
```

- Token 通过 HTTP Header 传递
- Token 有过期时间（通常 24h）
- 提供 Refresh Token 机制

---

### 限流

响应中包含限流信息：

```
X-RateLimit-Limit: 100        # 窗口内请求上限
X-RateLimit-Remaining: 95     # 剩余次数
X-RateLimit-Reset: 1620000000 # 窗口重置时间戳
```

---

## GraphQL 约定

### 命名

```graphql
# ✅ 好的命名
type User {
  id: ID!
  email: String!
  createdAt: DateTime!
}

# ❌ 坏的命名
type UserData { ... }        # 不需要 "Data" 后缀
type UserType { ... }        # 不需要 "Type" 后缀
```

### 分页

使用 Relay Connection 规范：

```graphql
users(first: 20, after: "cursor"): UserConnection!

type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
}
```
