# 如何启动
先确保装好依赖：在 d:\ml_pro_master\energy_llm 里执行 pip install fastapi uvicorn（若还没装 pydantic、starlette，这个命令会一起装好）。
启动服务：在同一路径下跑 uvicorn multi_energy_agent.api.main:app --reload --host 0.0.0.0 --port 8000。
PowerShell 直接执行上面命令即可；若用 python -m uvicorn 也同理。
启动后访问 http://127.0.0.1:8000/docs 可以调试 REST 接口；WebSocket 地址为 ws://127.0.0.1:8000/ws/scenarios/{run_id}，可用浏览器或 wscat 订阅事件。

# FastAPI 接口

该目录提供一个最小化 FastAPI 服务，能够将 `multi_energy_agent` 的 3-Agent 流水线暴露为 HTTP/WebSocket 接口，并向前端实时推送进度。

## 1. 安装与启动

```bash
pip install fastapi uvicorn
uvicorn multi_energy_agent.api.main:app --reload
```

启动后可通过 `http://localhost:8000/docs` 查看交互式接口文档。

## 2. 关键接口

| Method | Path | 描述 |
| ------ | ---- | ---- |
| `POST` | `/api/v1/scenarios` | 提交 `selection`/`scenario`/`inputs`（`scenario_id` 为必填），后台立即启动 Agent |
| `GET` | `/api/v1/scenarios` | 查询所有运行的状态汇总 |
| `GET` | `/api/v1/scenarios/{run_id}` | 查询单个运行的详情（包含 events、result、error） |
| `WS` | `/ws/scenarios/{run_id}` | 订阅推送事件，事件字段包含 `event/stage/message/payload` |

## 3. 事件类型

- `run_started` / `run_completed` / `run_failed`
- `stage_started` / `stage_completed`（stage 取 `intake`、`insight`、`report` 之一）

每个事件都会写入内存 store，并广播给 WebSocket 订阅者，方便前端渲染进度条或发送通知。
