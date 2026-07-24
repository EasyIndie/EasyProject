# 基础设施（Infrastructure）

> **🏢 基础设施即代码（IaC）。Docker、Terraform、Kubernetes、CI/CD。**

---

## 这是什么？

`infra/` 存放所有基础设施相关的代码和配置。这里的代码定义你的部署环境、容器编排、网络拓扑和 CI/CD 流水线。

---

## 目录结构

```
infra/
├── README.md              ← 你在这里
├── docker/                  Docker 配置
│   ├── Dockerfile.api       API 服务容器
│   └── docker-compose.yml   本地开发环境
├── terraform/               Terraform 模块
│   ├── main.tf              基础设施定义
│   └── variables.tf          变量定义
├── k8s/                     Kubernetes 清单
│   ├── deployment.yaml      部署清单
│   └── service.yaml         服务清单
└── ci/                      CI/CD 流水线定义
    └── deploy.yml           部署流水线
```

---

## 放什么？

- Dockerfile 和 docker-compose 文件
- Terraform 配置
- Kubernetes 清单
- CI/CD 流水线定义（非 GitHub Actions，那些在 `.github/workflows/`）
- 部署脚本和环境配置

## 不放什么？

- **GitHub Actions** → 放在 [`.github/workflows/`](../.github/workflows/)
- **应用程序代码** → 放在 [`apps/`](../apps/)
- **数据库迁移脚本** → 与代码一起管理，不放在 infra

---

## AI Agent 交互指南

1. **修改基础设施前**：理解当前的部署架构
2. **修改 Dockerfile 时**：确保镜像大小合理、层缓存有效
3. **修改 Terraform 时**：先运行 `terraform plan`，验证变更
4. **添加新服务时**：同时更新 docker-compose.yml 和 K8s 清单
5. **安全注意**：永远不要在 infra 代码中硬编码密钥

---

## 相关目录

- [`.github/workflows/`](../.github/workflows/) — GitHub Actions CI/CD
- [`scripts/`](../scripts/) — 部署和运维脚本
- [`docs/deployment.md`](../docs/deployment.md) — 部署文档
