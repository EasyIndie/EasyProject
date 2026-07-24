# 数据库标准

> **📏 数据模型命名、迁移、查询规范。**

---

## 命名规范

### 表/集合

```
✅ snake_case，单数形式：
   user
   order
   order_item
   payment_transaction

❌ 避免：
   Users           # 不要复数
   Order_Items     # 不要 PascalCase
   tbl_order       # 不要前缀
```

### 字段/列

```
✅ snake_case，见名知意：
   id
   email
   created_at
   updated_at
   deleted_at        # 软删除标记

❌ 避免：
   userId           # 保持 snake_case
   email_address    # 能简则简：email
```

### 索引

```
命名格式：idx_<table>_<column>

   idx_user_email
   idx_order_user_id
   idx_order_created_at
```

---

## 迁移策略

### 原则

- **每个 Schema 变更独立为一个迁移文件**
- **迁移必须是可逆的**：up 和 down 都要写
- **迁移脚本不含数据迁移**：Schema 变更和数据迁移分开
- **生产环境迁移前先在预发布环境验证**

### 迁移文件命名

```
YYYYMMDDHHMMSS_describe_change.sql

20240101120000_add_email_to_user.sql
20240102150000_create_order_table.sql
```

---

## 索引指南

### 何时创建索引

- 经常作为 WHERE 条件的字段
- 经常作为 JOIN 条件的字段
- 经常作为 ORDER BY 的字段
- 外键字段
- 唯一约束字段

### 何时不创建索引

- 表很小（< 1000 行）
- 字段写入远多于读取
- 字段选择性很低（如性别、布尔值）
- TEXT/BLOB 大字段（需要用专门的全文索引）

---

## 查询规范

### 通用

```sql
-- ✅ 明确列出需要的字段
SELECT id, name, email FROM user WHERE id = 1;

-- ❌ 永远不要 SELECT *
SELECT * FROM user;

-- ✅ 使用参数化查询防止 SQL 注入
SELECT * FROM user WHERE email = ?;  -- 参数绑定

-- ❌ 拼接 SQL 字符串
"SELECT * FROM user WHERE email = '" + email + "'";
```

### 分页

```sql
-- ✅ 游标分页（大数据量）
SELECT * FROM user
WHERE id > :last_id
ORDER BY id ASC
LIMIT 20;

-- ❌ 偏移分页（大偏移量时性能差）
SELECT * FROM user
ORDER BY id ASC
LIMIT 20 OFFSET 100000;
```

---

## ORM 使用指南

- **理解生成的 SQL**：不要盲目信任 ORM
- **注意 N+1 问题**：使用 eager loading
- **批量操作**：不要用 ORM 逐条处理大批量数据
- **复杂查询**：当 ORM 生成的 SQL 不够好时，手写 SQL

---

## 数据安全

- **敏感数据加密存储**：密码（bcrypt）、密钥（AES）
- **不要记录敏感数据到日志**：脱敏后再写入日志
- **连接使用 TLS**
- **遵循最小权限原则**：应用账号只给必要的权限
