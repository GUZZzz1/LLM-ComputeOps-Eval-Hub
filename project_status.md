# Project Status

## 当前版本

当前版本：`0.1.0`

项目当前处于本地/私有 LLM Gateway 与轻量 Eval Runner 的早期阶段，不是生产级模型服务平台。

## Day 1：私有 LLM Gateway

已完成：

- FastAPI 后端入口。
- SQLite 本地数据库初始化。
- 用户注册和登录。
- API Key 创建、HMAC-SHA256 hash 存储和 prefix 展示。
- `/api/models` 从数据库读取可用模型。
- `/v1/chat/completions` 转发到 Ollama `/api/chat`。
- OpenAI-compatible 风格响应。
- 成功和失败请求写入 `request_logs`。
- 当前用户请求日志列表和详情查询。
- Day 1 本地验证 Dev Console。
- `deployment/` 部署和环境准备文档。

接口和指标口径：

- `GET /api/requests` 返回字段名为 `requests`。
- `/v1/chat/completions` 的 `usage.input_tokens`、`usage.output_tokens`、`usage.total_tokens` 当前是 Day 1 估算值，规则为字符数 / 2。
- `metrics.ttft_ms` 当前为 `null`，因为 Day 1 固定 `stream=false`，不做首 token 流式计时。
- API Key 使用 HMAC-SHA256 hash 入库，pepper 来自 `API_KEY_PEPPER`，未设置时使用 `JWT_SECRET`。开发阶段如果修改 pepper 或升级 hash 规则，需要重新生成 API Key。

页面入口：

- `/` 是 Day 1 / Day 2 Dev Console，用于本地验证主链路，不是正式 Dashboard。
- `/api/docs` 是 FastAPI Swagger API 文档。
- `/docs` 是项目文档目录。
- `/deployment` 是部署和环境准备文档。

## Day 2：JSONL 批量评测 Runner

已完成：

- JSONL eval case loader。
- 默认样例：`eval_cases/smoke_cases.jsonl`。
- 同步批量 Eval Runner。
- 并发控制：`concurrency`。
- task timeout：`timeout_ms`。
- task retry：`retry_count`。
- rule-based evaluator。
- `eval_runs`、`eval_tasks`、`eval_results` 记录。
- `runs/<run_id>/run_summary.json` 最小报告。
- Dev Console 批量评测区域。
- CLI：`scripts/run_eval.py`。

规则评估器支持：

- `json_schema`
- `keyword`
- `contains`
- `exact`
- `tool_call`
- `safety_refusal`

Day 2 仍不包含：

- GPU 采样。
- Dashboard。
- LLM-as-judge。
- MindIE。
- RAG。
- Agent Harness。
- Prometheus/Grafana。
- 多机分布式压测。

## Day 2 API 示例

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

## CLI 示例

```bash
uv run python scripts/run_eval.py \
  --username eval_cli \
  --model qwen2.5:1.5b \
  --case-file eval_cases/smoke_cases.jsonl \
  --concurrency 2 \
  --timeout-ms 60000 \
  --retry-count 1
```

## 常用验收命令

```bash
python3 scripts/init_db.py
uv run pytest -q
uv run uvicorn backend.app.main:app --reload
```

## 后续边界

当前仍未做：

- GPU
- Dashboard
- MindIE
- Badcase regression set
- P95/P99 benchmark report
- LLM-as-judge
- 生产级异步任务队列
