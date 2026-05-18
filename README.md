# LLM ComputeOps & Eval Hub

Day 1 最小可运行版本：基于 FastAPI + SQLite + Ollama 搭建一个本地/私有 LLM 推理服务网关，支持用户注册登录、API Key 生成、OpenAI-compatible 风格请求、Ollama 转发和请求日志查询。

Day 1 暂不包含评测 runner、GPU 采样、Badcase 回流、Dashboard、MindIE、RAG、Browser Agent、Agent Harness、Prometheus/Grafana、模型-算力自动调度和复杂权限后台。这些属于后续阶段。

## 环境要求

- Python 3.11+
- Ollama
- SQLite

## 安装依赖

使用 `uv`：

```bash
uv sync
```

使用 `uv` 时，后续命令建议都通过 `uv run ...` 执行，这样不会依赖全局 PATH。

或使用 `pip`：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 环境变量

可参考 `.env.example`：

```bash
DATABASE_URL=sqlite:///data/app.db
OLLAMA_BASE_URL=http://localhost:11434
JWT_SECRET=dev-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

Day 1 默认会使用 `sqlite:///data/app.db` 和本机 Ollama 地址。

## 初始化数据库

macOS/Linux:

```bash
python3 scripts/init_db.py
```

Windows:

```powershell
python scripts/init_db.py
```

如果使用 `uv` 管理 Python，也可以运行：

```bash
uv run python scripts/init_db.py
```

该命令会自动创建 `data/`，创建 `users`、`api_keys`、`models`、`request_logs` 四张表，并初始化默认模型：

- provider: `ollama`
- model_name: `qwen2.5:1.5b`
- display_name: `Qwen2.5 1.5B via Ollama`

脚本可重复执行。

## 启动 Ollama

安装 Ollama 后启动服务：

```bash
ollama serve
```

拉取 Day 1 默认模型：

```bash
ollama pull qwen2.5:1.5b
```

## 启动 FastAPI

使用 `uv`：

```bash
uv run uvicorn backend.app.main:app --reload
```

如果已经激活 `.venv`：

```bash
uvicorn backend.app.main:app --reload
```

默认服务地址为 `http://localhost:8000`。

浏览器打开 `http://127.0.0.1:8000/` 会进入 Day 1 Web UI，可在页面内完成注册、登录、生成 API Key、调用模型和查看请求日志。

文档入口：

- 项目文档目录：`http://127.0.0.1:8000/docs`
- FastAPI Swagger：`http://127.0.0.1:8000/api/docs`
- OpenAPI JSON：`http://127.0.0.1:8000/api/openapi.json`

## 验收命令

健康检查：

```bash
curl http://localhost:8000/health
```

注册：

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"123456"}'
```

登录：

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"123456"}'
```

创建 API Key：

```bash
curl -X POST http://localhost:8000/api/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"local-test-key"}'
```

查看模型：

```bash
curl http://localhost:8000/api/models \
  -H "Authorization: Bearer <access_token>"
```

也可以使用 API Key：

```bash
curl http://localhost:8000/api/models \
  -H "Authorization: Bearer <api_key>"
```

请求模型：

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"qwen2.5:1.5b",
    "messages":[{"role":"user","content":"解释什么是 TTFT"}],
    "temperature":0.2,
    "max_tokens":256,
    "stream":false,
    "metadata":{"prompt_version":"v1","source":"manual_test"}
  }'
```

查看请求日志：

```bash
curl http://localhost:8000/api/requests \
  -H "Authorization: Bearer <access_token>"
```

限制返回条数，默认 20，最大 100：

```bash
curl "http://localhost:8000/api/requests?limit=50" \
  -H "Authorization: Bearer <access_token>"
```

查看请求详情：

```bash
curl http://localhost:8000/api/requests/<request_id> \
  -H "Authorization: Bearer <access_token>"
```

## Day 1 接口

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/api-keys`
- `GET /api/models`
- `POST /v1/chat/completions`
- `GET /api/requests`
- `GET /api/requests/{request_id}`

`/v1/chat/completions` 只接受 API Key，不接受登录 access token。管理接口使用登录 access token；`/api/models` 同时接受 access token 或 API Key。

## 文档结构

- `docs/index.html`: 浏览器文档目录页，对应 `/docs`。
- `docs/README.md`: 项目文档总览。
- `docs/day1.md`: Day 1 范围说明。
- `docs/api.md`: API 和文档路由说明。
- `docs/versions/0.1.0.md`: 当前 0.x 初版版本说明。
