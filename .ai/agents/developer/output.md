# 开发者 — 输出格式

## 输出内容

1. **代码文件**：修改或新增的源代码文件
2. **测试文件**：对应的测试代码
3. **任务更新**：任务文件中的 Result 部分已填写

## 输出示例

```
## 结果

### 实际做了什么
- 新增: apps/api/src/routes/auth.ts — POST /login 和 POST /register
- 修改: apps/api/src/middleware/auth.ts — 添加 JWT 验证中间件
- 新增: tests/unit/auth/login.test.ts — 登录接口单元测试

### 遇到的问题
- bcrypt 在 M1 Mac 上有兼容问题，改用 bcryptjs

### 注意事项
- Token 过期时间目前是硬编码的 24h，后续应该移到配置中
```
