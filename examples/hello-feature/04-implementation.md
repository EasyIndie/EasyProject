# 实现过程：健康检查接口

> **以下是一个 AI Agent 实现本功能时的叙事日志。展示了完整的开发流程。**

---

## T001: 创建 HealthService

### 认领任务

```bash
mv tasks/todo/T001-create-health-service.md tasks/doing/
```

### 创建分支

```bash
git checkout -b feature/health-check
```

### 实现

首先创建 `HealthService` 类。这个类需要：
1. 记录服务启动时间
2. 提供 `check()` 方法执行所有健康检查
3. 支持注册依赖检查器

```typescript
// apps/api/src/services/health.ts

/**
 * 健康检查服务。
 *
 * 职责:
 * - 检查自身状态（uptime）
 * - 协调依赖项的健康检查
 * - 汇总并返回健康报告
 */
export interface HealthCheckResult {
  status: 'healthy' | 'unhealthy';
  uptime: number;
  checks: Record<string, string>;
  timestamp: string;
}

export interface DependencyChecker {
  name: string;
  check: () => Promise<boolean>;
}

export class HealthService {
  private readonly startTime: number;
  private readonly checkers: DependencyChecker[] = [];

  constructor() {
    this.startTime = Date.now();
  }

  /** 注册一个依赖检查器 */
  registerChecker(checker: DependencyChecker): void {
    this.checkers.push(checker);
  }

  /** 执行所有健康检查 */
  async check(): Promise<HealthCheckResult> {
    const checks: Record<string, string> = {};

    for (const checker of this.checkers) {
      try {
        const isHealthy = await checker.check();
        checks[checker.name] = isHealthy ? 'healthy' : 'unhealthy';
      } catch (error) {
        checks[checker.name] = `unhealthy - ${error instanceof Error ? error.message : 'unknown error'}`;
      }
    }

    const allHealthy = Object.values(checks).every(
      (status) => status === 'healthy'
    );

    return {
      status: allHealthy ? 'healthy' : 'unhealthy',
      uptime: Math.floor((Date.now() - this.startTime) / 1000),
      checks,
      timestamp: new Date().toISOString(),
    };
  }
}
```

### 提交

```bash
git add apps/api/src/services/health.ts
git commit -m "feat: 添加 HealthService 核心逻辑

实现健康检查服务，支持注册依赖检查器并汇总结果。
Refs T001"
```

### 完成

```bash
mv tasks/doing/T001-create-health-service.md tasks/review/
```

---

## T002: 创建 /health 路由

```bash
mv tasks/todo/T002-create-health-route.md tasks/doing/
```

```typescript
// apps/api/src/routes/health.ts

import { Router } from 'express'; // 假设使用 Express
import { HealthService } from '../services/health';

export function createHealthRouter(healthService: HealthService): Router {
  const router = Router();

  router.get('/health', async (_req, res) => {
    try {
      const result = await healthService.check();
      const statusCode = result.status === 'healthy' ? 200 : 503;
      res.status(statusCode).json(result);
    } catch (error) {
      res.status(500).json({
        status: 'unhealthy',
        uptime: 0,
        checks: {},
        timestamp: new Date().toISOString(),
      });
    }
  });

  return router;
}
```

```bash
git add apps/api/src/routes/health.ts
git commit -m "feat: 添加 /health 路由

创建健康检查 HTTP 端点，根据检查结果返回 200 或 503。
Refs T002"
```

```bash
mv tasks/doing/T002-create-health-route.md tasks/review/
```

---

## T003: 集成到 App

```bash
mv tasks/todo/T003-integrate-health-route.md tasks/doing/
```

```typescript
// apps/api/src/app.ts (修改片段)

import { HealthService } from './services/health';
import { createHealthRouter } from './routes/health';

// ... 初始化服务 ...
const healthService = new HealthService();

// 注册数据库检查器
healthService.registerChecker({
  name: 'database',
  check: async () => {
    await db.raw('SELECT 1');
    return true;
  },
});

// 注册 Redis 检查器（如果项目使用）
// healthService.registerChecker({ ... });

// 在认证中间件之前注册健康检查路由
const healthRouter = createHealthRouter(healthService);
app.use(healthRouter); // /health 不需要认证

// ... 其他中间件和路由（认证、业务 API）...
```

```bash
git add apps/api/src/app.ts
git commit -m "feat: 集成 /health 路由到应用

在认证中间件之前注册健康检查路由，使其可公开访问。
Refs T003"
```

```bash
mv tasks/doing/T003-integrate-health-route.md tasks/review/
```

---

## Git 历史总览

```
* feat: 集成 /health 路由到应用 (T003)
* feat: 添加 /health 路由 (T002)
* feat: 添加 HealthService 核心逻辑 (T001)
* (main) 初始提交
```

---

## 下一步

进入测试阶段 — `05_test.md`
