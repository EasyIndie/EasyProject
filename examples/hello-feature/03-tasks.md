# 任务拆解：健康检查接口

---

## 任务列表

| 序号 | 任务 | 依赖 | 预估 |
|------|------|------|------|
| T001 | 创建 HealthService 核心逻辑 | - | 0.5d |
| T002 | 创建 /health 路由 | T001 | 0.5d |
| T003 | 集成到 App（跳过认证） | T002 | 0.25d |
| T004 | 编写测试 | T001,T002,T003 | 0.5d |

---

## 依赖图

```
T001 ──→ T002 ──→ T003 ──→ T004
```

---

## 关键路径

T001 → T002 → T003 → T004（总共约 1.75 天）

---

## 各任务详情

### T001: 创建 HealthService

- **目标**：实现健康检查的核心业务逻辑
- **产出**：`apps/api/src/services/health.ts`
- **内容**：
  - `HealthService.check()` 方法
  - 自身状态检查（uptime）
  - 依赖检查接口定义
  - 汇总所有检查结果

### T002: 创建 /health 路由

- **目标**：暴露 HTTP 端点
- **产出**：`apps/api/src/routes/health.ts`
- **内容**：
  - `GET /health` 路由处理函数
  - 调用 HealthService
  - 根据结果返回 200 或 503

### T003: 集成到 App

- **目标**：将路由注册到应用，配置跳过认证
- **产出**：`apps/api/src/app.ts`（修改）
- **内容**：
  - 注册 `/health` 路由
  - 在认证中间件之前注册（跳过认证）

### T004: 编写测试

- **目标**：确保功能正确且不回归
- **产出**：
  - `tests/unit/health.service.test.ts`
  - `tests/integration/health.test.ts`
- **内容**：
  - 正常情况返回 200
  - 依赖失败返回 503
  - 响应包含 uptime
  - 响应时间 < 50ms

---

## 下一步

开始实现 — 从 T001 开始
