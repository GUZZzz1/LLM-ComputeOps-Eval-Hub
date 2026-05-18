# LLM ComputeOps & Eval Hub

## 1. 项目介绍

LLM ComputeOps & Eval Hub 是一个本地/私有 LLM 推理服务网关项目。

当前 Day 1 版本聚焦最小闭环：用户注册、登录、生成 API Key、通过 API Key 调用 `/v1/chat/completions`，后端转发到本地 Ollama，并记录请求日志。

这个阶段的目标是验证基础网关链路，不是完整评测平台，也不是生产级模型服务平台。

## 2. Quickstart

本地启动、初始化数据库、Ollama 配置和接口调用命令见：

- [deployment/index.html](./deployment/index.html)

依赖准备文档：

- [macOS 依赖与准备](./deployment/setup-macos.html)
- [Windows 依赖与准备](./deployment/setup-windows.html)

本地页面入口：

- Web UI: `http://127.0.0.1:8000/`
- 部署文档: `http://127.0.0.1:8000/deployment`
- Swagger API 文档: `http://127.0.0.1:8000/api/docs`

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
