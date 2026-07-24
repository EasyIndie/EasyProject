# 部署文档

> **🚀 如何部署和运维本项目。**

---

## 环境

| 环境 | 用途 | 触发方式 |
|------|------|----------|
| **开发（dev）** | 本地开发 | 自动（docker-compose） |
| **预发布（staging）** | 上线前验证 | PR 合并后自动部署 |
| **生产（production）** | 线上服务 | 手动触发或 CD 自动 |

---

## 首次部署

（根据项目实际情况填充。以下为模板。）

```bash
# 1. 构建镜像
docker build -t PROJECT_NAME:latest .

# 2. 运行容器
docker-compose up -d

# 3. 运行数据库迁移
make migrate

# 4. 验证部署
curl http://localhost:8080/health
```

---

## 部署流程

```
开发者提交代码 → PR Review → 合并到 main
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
              CI: 构建镜像                CI: 运行测试
                    │                           │
                    ▼                           ▼
              推送镜像到 Registry        测试通过
                    │
                    ▼
              部署到 staging 环境
                    │
                    ▼
              在 staging 上验证
                    │
                    ▼
              手动触发生产部署
                    │
                    ▼
              监控 & 验证
```

---

## 回滚

```bash
# 如果新版本有问题，回滚到上一个版本
docker-compose down
docker-compose -f docker-compose.prev.yml up -d

# 或使用 K8s 回滚
kubectl rollout undo deployment/PROJECT_NAME
```

---

## 环境变量

（由 `bootstrap.sh` 根据项目技术栈初始化）
