# 架构师 — 输出格式

## 输出内容

1. **架构设计文档** — 方案概述、组件图、关键决策
2. **ADR 文件**（如果需要）— `architecture/adr/NNNN-*.md`
3. **API 规格**（如果涉及 API）— `specs/<feature>/api.md`

## 输出示例

```
# 架构设计：user-auth

## 方案概述
采用 JWT 无状态认证方案。客户端在 Authorization Header
中携带 Bearer Token。服务端通过中间件验证 Token 并注入
用户上下文。

## 组件图
Client → API Gateway (JWT Middleware) → Auth Service → DB

## 关键决策
| 决策 | 方案 | 理由 | ADR |
|------|------|------|-----|
| 认证方式 | JWT | 无状态、可扩展 | ADR-0003 |
| Token 存储 | HttpOnly Cookie | 防 XSS | - |
```
