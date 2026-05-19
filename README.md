# LLM ComputeOps & Eval Hub

## 1. 项目介绍

LLM ComputeOps & Eval Hub 是一个本地/私有 LLM Gateway 与轻量 Eval Runner 项目。

当前项目已经完成：

- Day 1：私有 LLM Gateway，支持注册登录、API Key、Ollama 转发和请求日志。
- Day 2：JSONL 批量评测 Runner，支持规则评估、并发、timeout/retry 和 run summary。

项目目标是验证本地私有 LLM 调用与最小批量评测链路，不是生产级模型服务平台。

## 2. Quickstart

本地启动、初始化数据库、Ollama 配置和运行命令见：

- [deployment/index.html](./deployment/index.html)

依赖准备文档：

- [macOS 依赖与准备](./deployment/setup-macos.html)
- [Windows 依赖与准备](./deployment/setup-windows.html)

本地页面入口：

- Web UI: `http://127.0.0.1:8000/`
- 项目文档: `http://127.0.0.1:8000/docs`
- 部署文档: `http://127.0.0.1:8000/deployment`
- Swagger API 文档: `http://127.0.0.1:8000/api/docs`

## 3. 版本情况

Day 1、Day 2 的完成情况、接口示例、指标说明和后续边界见：

- [project_status.md](./project_status.md)
