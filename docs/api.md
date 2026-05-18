# API 路由

## 文档路由

- `GET /docs`: 项目文档目录页。
- `GET /docs/README.md`: 文档总览 Markdown。
- `GET /docs/day1.md`: Day 1 范围说明。
- `GET /docs/api.md`: API 路由说明。
- `GET /docs/versions/0.1.0.md`: 版本说明。
- `GET /api/docs`: FastAPI Swagger UI。
- `GET /api/redoc`: FastAPI ReDoc。
- `GET /api/openapi.json`: OpenAPI schema。

## Day 1 业务路由

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/api-keys`
- `GET /api/models`
- `POST /v1/chat/completions`
- `GET /api/requests`
- `GET /api/requests/{request_id}`

## 鉴权边界

- 管理接口使用登录后返回的 access token。
- `/v1/chat/completions` 只接受 API Key。
- `/api/models` 同时接受 access token 或 API Key，方便 Web UI 和外部调用方检查可用模型。
