# LLM ComputeOps & Eval Hub

## 1. 项目介绍

LLM ComputeOps & Eval Hub 是一个本地/私有 LLM 推理服务网关项目。

当前 Day 1 版本聚焦最小闭环：用户注册、登录、生成 API Key、通过 API Key 调用 `/v1/chat/completions`，后端转发到本地 Ollama，并记录请求日志。

Day 2 在此基础上新增 JSONL 批量评测 runner，用于验证一批 eval cases 的模型输出和规则评估结果。

当前目标是验证本地私有 LLM Gateway 和最小批量评测链路，不是生产级模型服务平台。

## 2. Quickstart

本地启动、初始化数据库、Ollama 配置和接口调用命令见：

- [deployment/index.html](./deployment/index.html)

依赖准备文档：

- [macOS 依赖与准备](./deployment/setup-macos.html)
- [Windows 依赖与准备](./deployment/setup-windows.html)

本地页面入口：

- Web UI: `http://127.0.0.1:8000/`
- 项目文档: `http://127.0.0.1:8000/docs`
- 部署文档: `http://127.0.0.1:8000/deployment`
- Swagger API 文档: `http://127.0.0.1:8000/api/docs`

说明：

- `/` 是 Day 1 Dev Console，用于本地验证主链路，不是正式 Dashboard。
- `/api/docs` 是 FastAPI Swagger API 文档。
- `/docs` 是项目文档目录。
- `/deployment` 是部署和环境准备文档。

## 3. 当前进度

当前版本：`0.1.0`

已完成：

- FastAPI 后端入口。
- SQLite 本地数据库初始化。
- 用户注册和登录。
- API Key 创建、hash 存储和 prefix 展示。
- `/api/models` 从数据库读取可用模型。
- `/v1/chat/completions` 转发到 Ollama `/api/chat`。
- OpenAI-compatible 风格响应。
- 成功和失败请求写入 `request_logs`。
- 当前用户请求日志列表和详情查询。
- Day 1 本地验证 Web UI。
- `deployment/` 部署和环境准备文档。
- JSONL eval case loader。
- 同步批量 Eval Runner。
- 并发控制、timeout 和 retry。
- rule-based evaluator。
- `eval_runs`、`eval_tasks`、`eval_results` 记录。
- `runs/<run_id>/run_summary.json` 最小报告。
- Dev Console 批量评测区域。

接口和指标口径：

- `GET /api/requests` 返回字段名为 `requests`。
- `/v1/chat/completions` 的 `usage.input_tokens`、`usage.output_tokens`、`usage.total_tokens` 当前是 Day 1 估算值，规则为字符数 / 2。
- `metrics.ttft_ms` 当前为 `null`，因为 Day 1 固定 `stream=false`，不做首 token 流式计时。
- API Key 使用 HMAC-SHA256 hash 入库，pepper 来自 `API_KEY_PEPPER`，未设置时使用 `JWT_SECRET`。Day 1 开发阶段如果修改 pepper 或升级到该 hash 规则，需要重新生成 API Key。

## 4. Day 2 批量评测

Day 2 新增：

- JSONL eval case：默认样例位于 `eval_cases/smoke_cases.jsonl`。
- batch runner：批量读取 cases 并调用现有 Ollama provider。
- concurrency：用 asyncio semaphore 控制并发。
- timeout / retry：按 task 控制超时和重试。
- rule-based evaluator：支持 `json_schema`、`keyword`、`contains`、`exact`、`tool_call`、`safety_refusal`。
- eval 记录：写入 `eval_runs`、`eval_tasks`、`eval_results`。
- run summary：输出 `runs/<run_id>/run_summary.json`。

Day 2 仍不包含：

- GPU 采样。
- Dashboard。
- LLM-as-judge。
- MindIE。
- RAG。
- Agent Harness。
- Prometheus/Grafana。
- 多机分布式压测。

### API 示例

登录：

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"123456"}'
```

创建 API Key，如需要继续验证单次模型请求：

```bash
curl -X POST http://127.0.0.1:8000/api/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"day2-check-key"}'
```

运行批量评测：

```bash
curl -X POST http://127.0.0.1:8000/api/eval/runs \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"smoke-eval",
    "model":"qwen2.5:1.5b",
    "case_file":"eval_cases/smoke_cases.jsonl",
    "concurrency":2,
    "timeout_ms":60000,
    "retry_count":1
  }'
```

查看 run：

```bash
curl http://127.0.0.1:8000/api/eval/runs/<run_id> \
  -H "Authorization: Bearer <access_token>"
```

查看 tasks：

```bash
curl http://127.0.0.1:8000/api/eval/runs/<run_id>/tasks \
  -H "Authorization: Bearer <access_token>"
```

查看 results：

```bash
curl http://127.0.0.1:8000/api/eval/runs/<run_id>/results \
  -H "Authorization: Bearer <access_token>"
```

### CLI 示例

```bash
uv run python scripts/run_eval.py \
  --username eval_cli \
  --model qwen2.5:1.5b \
  --case-file eval_cases/smoke_cases.jsonl \
  --concurrency 2 \
  --timeout-ms 60000 \
  --retry-count 1
```

## 5. 后续边界

后续只考虑：

- JSONL eval case runner。
- 批量请求。
- 并发控制。
- timeout / retry。
- eval_result 初步记录。

当前仍未做 GPU、Dashboard、MindIE、Badcase regression set、P95/P99 benchmark report。

常用验收命令：

```bash
python3 scripts/init_db.py
uv run pytest -q
uv run uvicorn backend.app.main:app --reload
```
