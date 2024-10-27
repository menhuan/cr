
# Code Review Service 部署指南

## 目录
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [API使用](#api使用)
- [故障排查](#故障排查)
- [常见问题](#常见问题)

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- GitLab 访问权限
- 8000 端口可用

## 快速开始

### 1. 克隆代码仓库
```bash
git clone <repository-url>
cd code-review-service
```

### 2. 配置环境变量
```bash
cp .env.example .env
```

编辑 `.env` 文件:
```env
GITLAB_TOKEN=your_gitlab_token
GITLAB_URL=https://gitlab.com
```

### 3. 启动服务
```bash
docker-compose up -d
```

### 4. 验证服务
```bash
# 健康检查
curl http://localhost:8000/health

# API文档访问
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

## 详细配置

### Docker Compose 配置

```yaml
version: '3.8'

services:
  code-review-service:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: code-review-service
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./src:/app/src
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

networks:
  default:
    name: code-review-network
```

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY .env .

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["python", "src/main.py"]
```

### 环境变量说明

| 变量名 | 说明 | 必填 | 默认值 |
|--------|------|------|--------|
| GITLAB_TOKEN | GitLab 访问令牌 | 是 | - |
| GITLAB_URL | GitLab 实例地址 | 否 | https://gitlab.com |

## API使用

### 代码评审接口

**请求**:
```bash
curl -X POST http://localhost:8000/api/v1/code-review \
-H "Content-Type: application/json" \
-d '{
    "mr_url": "https://gitlab.com/group/project/-/merge_requests/1",
    "submit_comment": true,
    "line_comments": true
}'
```

**参数说明**:
- `mr_url`: GitLab MR URL
- `submit_comment`: 是否提交总评论
- `line_comments`: 是否提交行评论

**响应示例**:
```json
{
    "status": "success",
    "message": "Code review completed successfully",
    "review_results": {
        "mr_info": {
            "title": "Feature: Add new functionality",
            "author": {
                "id": 1,
                "name": "John Doe",
                "username": "johndoe"
            },
            "state": "opened",
            "created_at": "2024-01-01T00:00:00Z"
        },
        "review_results": {
            "summary": {
                "total_files": 5,
                "total_additions": 100,
                "total_deletions": 50
            }
        }
    }
}
```

## 服务管理命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 进入容器
docker-compose exec code-review-service bash
```

## 故障排查

### 服务无法启动
1. 检查环境变量配置
```bash
cat .env
```

2. 检查容器日志
```bash
docker-compose logs -f code-review-service
```

3. 检查端口占用
```bash
netstat -tulpn | grep 8000
```

### API 访问失败
1. 确认服务状态
```bash
docker-compose ps
```

2. 测试健康检查接口
```bash
curl http://localhost:8000/health
```

### GitLab 连接问题
1. 验证 Token 权限
2. 检查网络连接
3. 确认 GitLab URL 配置

## 常见问题

Q: 如何更新服务？
```bash
git pull
docker-compose up -d --build
```

Q: 如何查看具体错误信息？
```bash
docker-compose logs -f code-review-service
```

Q: 如何修改配置后重新加载？
```bash
# 修改 .env 文件后执行
docker-compose restart
```

## 安全提示

1. 环境变量安全
   - 不要提交 `.env` 到版本控制
   - 定期更换 GitLab Token
   - 限制文件访问权限

2. 网络安全
   - 建议配置 HTTPS
   - 限制 API 访问来源
   - 添加适当的认证机制

## 扩展阅读

- [GitLab API 文档](https://docs.gitlab.com/ee/api/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)

## 支持与反馈

如有问题或建议，请：
1. 提交 Issue
2. 联系维护团队
3. 查阅在线文档

---

**注意**: 本文档持续更新中，如发现问题请及时反馈。