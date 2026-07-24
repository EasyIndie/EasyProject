# 代码文件头模板

以下模板用于新建源代码文件时在文件顶部添加注释头。根据语言选择对应的注释语法。

---

## 通用格式

```
简短的一句文件用途说明

职责：
- 这个文件负责什么
- 不负责什么

关联：
- 相关的 Issue/ADR/文档
```

---

## 按语言

### TypeScript / JavaScript

```typescript
/**
 * 文件名: auth.service.ts
 * 用途: 用户认证服务，处理登录、注册、Token 管理
 *
 * 职责:
 * - 用户登录/注册逻辑
 * - JWT Token 生成与验证
 * - 密码哈希与校验
 *
 * 不负责:
 * - HTTP 请求处理（那是 controller 的事）
 * - 数据库直接操作（那是 repository 的事）
 */
```

### Python

```python
"""
文件名: auth_service.py
用途: 用户认证服务，处理登录、注册、Token 管理

职责:
- 用户登录/注册逻辑
- JWT Token 生成与验证
- 密码哈希与校验

不负责:
- HTTP 请求处理（那是 view 的事）
- 数据库直接操作（那是 repository 的事）
"""
```

### Go

```go
// 文件名: auth_service.go
// 用途: 用户认证服务，处理登录、注册、Token 管理
//
// 职责:
//   - 用户登录/注册逻辑
//   - JWT Token 生成与验证
//   - 密码哈希与校验
//
// 不负责:
//   - HTTP 请求处理（那是 handler 的事）
//   - 数据库直接操作（那是 repository 的事）
```

### Rust

```rust
//! 文件名: auth_service.rs
//! 用途: 用户认证服务，处理登录、注册、Token 管理
//!
//! 职责:
//! - 用户登录/注册逻辑
//! - JWT Token 生成与验证
//! - 密码哈希与校验
//!
//! 不负责:
//! - HTTP 请求处理（那是 handler 的事）
//! - 数据库直接操作（那是 repository 的事）
```
