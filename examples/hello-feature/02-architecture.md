# 架构设计：健康检查接口

---

## 方案概述

在 API 服务中新增一个 `GET /health` 端点。该端点不经过认证中间件，直接返回服务的健康状态。健康检查逻辑包括：自身存活检查 + 依赖项探测（数据库、缓存等）。

---

## 组件图

```text
                    Load Balancer
                         │
                    GET /health (每 10s)
                         │
                    ┌────▼────┐
                    │  API    │
                    │  Server │
                    └────┬────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
       ┌────▼───┐  ┌────▼───┐  ┌────▼───┐
       │  DB    │  │ Redis  │  │  ...   │
       │ (Ping) │  │ (Ping) │  │        │
       └────────┘  └────────┘  └────────┘
```

---

## 数据流

1. 负载均衡器 / 监控系统 → `GET /health`
2. API Server → `HealthService.check()`
3. `HealthService` → 检查自身状态（memory, uptime）
4. `HealthService` → Ping 数据库（`SELECT 1`）
5. `HealthService` → Ping Redis（`PING`）
6. 收集所有结果 → 生成 JSON 响应

---

## API 设计

### GET /health

**成功响应（200）**：

```json
{
  "status": "healthy",
  "uptime": 3600,
  "checks": {
    "database": "healthy",
    "cache": "healthy"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**失败响应（503）**：

```json
{
  "status": "unhealthy",
  "uptime": 3600,
  "checks": {
    "database": "healthy",
    "cache": "unhealthy - connection timeout"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/routes/health.ts` | 新增 | 健康检查路由 |
| `apps/api/src/services/health.ts` | 新增 | 健康检查业务逻辑 |
| `apps/api/src/app.ts` | 修改 | 注册 `/health` 路由（跳过认证） |
| `tests/unit/health.service.test.ts` | 新增 | 单元测试 |
| `tests/integration/health.test.ts` | 新增 | 集成测试 |

---

## 关键设计决策

| 决策 | 方案 | 理由 |
|------|------|------|
| 端点路径 | `/health` 而非 `/api/v1/health` | 这是基础设施端点，不属于业务 API |
| 是否暴露详情 | 暴露依赖状态 | 帮助快速定位故障；内部网络，安全风险低 |
| 依赖超时 | 每个依赖 Ping 超时 2 秒 | 太短导致误报，太长影响响应时间 |
| 是否经过认证 | 不经过认证 | 负载均衡器和监控系统需要访问 |

---

## 安全考量

- 健康检查端点不暴露敏感数据（如数据库密码、连接字符串）
- 在公网环境下应限制访问来源 IP
- 不暴露内部服务的详细信息（如 IP 地址）

---

## 下一步

进入 `03_tasks.md` — 任务拆解
