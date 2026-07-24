# 数据模型

> **🗄️ 数据模型设计与迁移策略。**

---

## 实体关系概览

（根据项目实际情况填充。以下为模板。）

```text
┌──────────┐       ┌──────────┐
│   User   │───┬──→│  Order   │
└──────────┘   │   └──────────┘
               │
               │   ┌──────────┐
               └──→│  Session │
                   └──────────┘
```

---

## 关键实体

### User

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 邮箱 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |
| deleted_at | TIMESTAMP | NULL | 软删除标记 |

---

## 迁移策略

- 使用迁移工具管理 Schema 变更
- 每个迁移文件可逆（有 up 和 down）
- 生产环境迁移前在 staging 上测试
- 大表变更使用在线迁移（避免锁表）

---

## 数据安全

- 敏感字段加密存储（使用 AES-256-GCM）
- 密码使用 bcrypt 哈希
- 数据库连接使用 TLS
- 遵循最小权限原则（应用账号只授予必要的 CRUD 权限）

---

## 相关文档

- 数据库命名与查询标准：`docs/standards/database.md`
- 查询性能优化：`docs/standards/database.md`
