# Quickstart

本文档用于本地部署 Day 1 最小可运行版本：注册、登录、创建 API Key、调用 Ollama、记录并查询请求日志。

## 项目目录

```text
backend/
  app/
    main.py
    config.py
    db.py
    auth.py
    schemas.py
    providers/
      base.py
      ollama.py
    services/
      request_logger.py
scripts/
  init_db.py
data/
  app.db
docs/
  index.html
  README.md
  day1.md
  api.md
  versions/
    0.1.0.md
README.md
QUICKSTART.md
.env.example
pyproject.toml
```

## 目录和文件说明

- `backend/app/main.py`: FastAPI 入口，包含健康检查、注册、登录、API Key、模型列表、聊天转发、请求日志查询接口。
- `backend/app/config.py`: 读取环境变量，提供 SQLite 路径解析。
- `backend/app/db.py`: SQLite 连接和建表逻辑。
- `backend/app/auth.py`: 密码 hash、登录 JWT、API Key 生成和鉴权。
- `backend/app/schemas.py`: Pydantic 请求/响应模型。
- `backend/app/providers/base.py`: Provider 统一响应结构。
- `backend/app/providers/ollama.py`: Ollama `/api/chat` 调用封装，统一错误和指标返回。
- `backend/app/services/request_logger.py`: 写入 `request_logs` 的请求日志服务。
- `scripts/init_db.py`: 初始化数据库，创建 4 张表并插入默认模型。
- `data/app.db`: 本地 SQLite 数据库文件，初始化后生成。
- `docs/`: 项目文档目录，`/docs` 展示目录页，Swagger 位于 `/api/docs`。
- `.env.example`: 环境变量示例。
- `pyproject.toml`: Python 依赖声明。

## 已实现功能

- 用户注册：`POST /api/auth/register`
- 用户登录：`POST /api/auth/login`
- 创建 API Key：`POST /api/api-keys`
- 查询可用模型：`GET /api/models`
- OpenAI-compatible 风格聊天接口：`POST /v1/chat/completions`
- 转发到本地 Ollama：`OLLAMA_BASE_URL/api/chat`
- 成功和失败请求都写入 `request_logs`
- 查询当前用户请求日志：`GET /api/requests`
- 查询当前用户单条请求详情：`GET /api/requests/{request_id}`

Day 1 没有实现前端、评测 runner、GPU 采样、Dashboard、Badcase、RAG、Agent Harness、Prometheus/Grafana 和复杂权限系统。

## macOS 部署

### 1. 安装 Python 依赖

推荐使用 `uv`：

```bash
uv sync
```

或使用 `pip`：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. 安装 Ollama

使用 Homebrew：

```bash
brew install ollama
```

也可以从官网下载 macOS 安装包：

```text
https://ollama.com/download
```

### 3. 启动 Ollama

```bash
ollama serve
```

保持该终端窗口运行。另开一个终端拉取默认模型：

```bash
ollama pull qwen2.5:1.5b
```

### 4. 初始化数据库

```bash
python3 scripts/init_db.py
```

也可以使用 `uv` 管理的 Python：

```bash
uv run python scripts/init_db.py
```

### 5. 启动 FastAPI

如果使用 `uv sync` 安装依赖，直接运行：

```bash
uv run uvicorn backend.app.main:app --reload
```

如果使用 `pip` 并且已经激活 `.venv`，运行：

```bash
uvicorn backend.app.main:app --reload
```

如果看到 `Address already in use`，说明 `8000` 端口已有服务在运行。可以先查看占用进程：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

如果是你之前启动的 `uvicorn`，在对应终端按 `Ctrl+C` 停掉；或者换一个端口启动：

```bash
uv run uvicorn backend.app.main:app --reload --port 8001
```

浏览器打开 `http://127.0.0.1:8000/` 会进入 Day 1 Web UI，可在页面内完成注册、登录、生成 API Key、调用模型和查看请求日志。

项目文档目录可访问 `http://127.0.0.1:8000/docs`。FastAPI Swagger API 文档可访问 `http://127.0.0.1:8000/api/docs`。

## Windows 部署

### 1. 安装 Python

安装 Python 3.11+，并确认命令可用：

```powershell
python --version
```

### 2. 安装 Python 依赖

使用 `uv`：

```powershell
uv sync
```

或使用 `pip`：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

如果 PowerShell 禁止激活虚拟环境，可先执行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. 安装 Ollama

从官网下载 Windows 安装包：

```text
https://ollama.com/download
```

安装后打开新的 PowerShell，确认：

```powershell
ollama --version
```

### 4. 拉取默认模型

```powershell
ollama pull qwen2.5:1.5b
```

Windows 版 Ollama 通常会随应用自动启动服务。如果没有启动，可运行：

```powershell
ollama serve
```

### 5. 初始化数据库

```powershell
python scripts/init_db.py
```

### 6. 启动 FastAPI

如果使用 `uv sync` 安装依赖，直接运行：

```powershell
uv run uvicorn backend.app.main:app --reload
```

如果使用 `pip` 并且已经激活 `.venv`，运行：

```powershell
uvicorn backend.app.main:app --reload
```

## 接口冒烟测试

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

查看请求详情：

```bash
curl http://localhost:8000/api/requests/<request_id> \
  -H "Authorization: Bearer <access_token>"
```
