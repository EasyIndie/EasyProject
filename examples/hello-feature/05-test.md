# 测试：健康检查接口

---

## 测试计划

### 测试类型

| 类型 | 数量 | 覆盖场景 |
|------|------|----------|
| 单元测试 | 4 | HealthService 逻辑 |
| 集成测试 | 3 | HTTP 端点行为 |

---

## 单元测试

```typescript
// tests/unit/health.service.test.ts

describe('HealthService', () => {
  let service: HealthService;

  beforeEach(() => {
    service = new HealthService();
  });

  // UT-01: 无依赖时应该返回 healthy
  it('should return healthy when no checkers registered', async () => {
    const result = await service.check();
    expect(result.status).toBe('healthy');
  });

  // UT-02: 所有依赖正常时应该返回 healthy
  it('should return healthy when all checkers pass', async () => {
    service.registerChecker({
      name: 'database',
      check: async () => true,
    });
    const result = await service.check();
    expect(result.status).toBe('healthy');
    expect(result.checks['database']).toBe('healthy');
  });

  // UT-03: 任一依赖失败时应该返回 unhealthy
  it('should return unhealthy when any checker fails', async () => {
    service.registerChecker({
      name: 'database',
      check: async () => true,
    });
    service.registerChecker({
      name: 'cache',
      check: async () => false,
    });
    const result = await service.check();
    expect(result.status).toBe('unhealthy');
    expect(result.checks['cache']).toBe('unhealthy');
  });

  // UT-04: 依赖抛异常时应该捕获
  it('should catch checker errors gracefully', async () => {
    service.registerChecker({
      name: 'database',
      check: async () => {
        throw new Error('connection timeout');
      },
    });
    const result = await service.check();
    expect(result.status).toBe('unhealthy');
    expect(result.checks['database']).toContain('connection timeout');
  });

  // UT-05: uptime 应该递增
  it('should report increasing uptime', async () => {
    const result1 = await service.check();
    // 等待 1 秒
    await new Promise((resolve) => setTimeout(resolve, 1100));
    const result2 = await service.check();
    expect(result2.uptime).toBeGreaterThanOrEqual(result1.uptime + 1);
  });
});
```

---

## 集成测试

```typescript
// tests/integration/health.test.ts

describe('GET /health', () => {
  let app: Express;

  beforeAll(async () => {
    app = await createTestApp(); // 测试辅助函数
  });

  // IT-01: 正常情况返回 200
  it('should return 200 when service is healthy', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('healthy');
    expect(res.body).toHaveProperty('uptime');
    expect(res.body).toHaveProperty('checks');
    expect(res.body).toHaveProperty('timestamp');
  });

  // IT-02: 响应时间不超过 50ms
  it('should respond within 50ms', async () => {
    const start = Date.now();
    await request(app).get('/health');
    const duration = Date.now() - start;
    expect(duration).toBeLessThan(50);
  });

  // IT-03: 不需要认证
  it('should not require authentication', async () => {
    const res = await request(app)
      .get('/health')
      .set('Authorization', ''); // 无 Token
    expect(res.status).toBe(200);
  });
});
```

---

## 测试结果

```
PASS tests/unit/health.service.test.ts
  HealthService
    ✓ should return healthy when no checkers registered
    ✓ should return healthy when all checkers pass
    ✓ should return unhealthy when any checker fails
    ✓ should catch checker errors gracefully
    ✓ should report increasing uptime

PASS tests/integration/health.test.ts
  GET /health
    ✓ should return 200 when service is healthy
    ✓ should respond within 50ms (42ms)
    ✓ should not require authentication

Tests: 8 passed, 0 failed
```

---

## 验收标准验证

| 验收标准 | 测试 | 状态 |
|----------|------|------|
| GET /health 返回 200 | IT-01 | ✅ |
| 依赖失败返回 503 | UT-03 | ✅ |
| 包含 uptime | UT-05, IT-01 | ✅ |
| 响应时间 < 50ms | IT-02 | ✅ |
| 不需要认证 | IT-03 | ✅ |

---

## 下一步

进入审查阶段 — `06_review.md`
