# Day 1 范围

Day 1 的目标是跑通最小推理网关链路：

1. 用户注册。
2. 用户登录并获得 access token。
3. 使用 access token 创建 API Key。
4. 使用 API Key 请求 `/v1/chat/completions`。
5. 后端转发到 Ollama `/api/chat`。
6. 返回 OpenAI-compatible 风格响应。
7. 写入 `request_logs`。
8. 用户查询自己的请求日志。

## 已包含

- FastAPI 后端。
- SQLite 本地数据库。
- 手写 JWT 风格 access token。
- API Key 生成、hash 存储和 prefix 展示。
- Ollama provider 转发。
- 成功和失败请求日志。
- Day 1 开发验证 Web UI。

## 暂不包含

- JSONL eval case runner。
- 批量请求和并发控制。
- timeout / retry 策略编排。
- eval_result 记录。
- GPU 采样。
- Dashboard。
- RAG。
- MindIE。
- Agent Harness。
- 多租户权限后台。
