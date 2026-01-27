## 1) 如何运行（你拿到 zip 解压后即可）

在项目根目录（energy_llm/）：

### 方式 A：直接跑 demo（会自动调用 fhd/lyx/eco_knowledge_graph）

```bash
python -m multi_energy_agent.runner
```

会生成：

* `outputs/demo-liuzhou/report.md`
* `outputs/demo-liuzhou/report.pdf`
* `logs_running/<timestamp>_demo-liuzhou.log`
* `logs_llm_direct/<timestamp>_demo-liuzhou.jsonl`

### 方式 B：自定义 selection（推荐你们后续用）

```python
from multi_energy_agent.runner import run_scenario

state = run_scenario(
    selection={"metadata": {"city": "柳州", "industry_keywords": ["汽车", "机械"]}},
    scenario={"scenario_id": "my-park", "baseline_year": 2023},
    inputs={}
)
print(state["envelopes"]["report"]["artifacts"]["report_pdf_path"])
```

## 2) FastAPI 接口速览（来自 `API使用指南.md`）

### 启动与文档

```bash
# 安装依赖（若未安装）
pip install fastapi uvicorn

# 推荐：使用脚本启动
./start_api.sh

# 或直接运行 uvicorn
uvicorn multi_energy_agent.api.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后可访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/healthz

### 常用端点

- `GET /healthz`：返回 `{"status": "ok", "stages": "intake,insight,report"}` 用于探活
- `POST /api/v1/scenarios`：提交 `selection / scenario / inputs` 创建或运行场景
- `GET /api/v1/scenarios`：列出所有运行及状态
- `GET /api/v1/scenarios/{run_id}`：查看运行详情、事件与产物
- `GET /api/v1/scenarios/{scenario_id}/qa/suggestions`：获取建议问题
- `POST /api/v1/scenarios/{scenario_id}/qa?question=...`：根据报告内容进行问答
- WebSocket（`/ws/scenarios/{run_id}`）可实时订阅运行事件（参见原指南）

### 测试脚本

项目内置 `relative_tests/test_api.py` 用于端到端检测：

```bash
./start_api.sh                             # 先确保服务运行
python relative_tests/test_api.py          # 另一个终端执行
```

脚本会依次调用健康检查、创建场景、查询运行状态，并以 JSON 打印每个阶段的响应，便于快速验证后端是否可用。

## 3) Web / CLI 问答演示（来自 `demo_qa.sh` 与 `Web界面使用说明.md`）

### 一键脚本

```bash
./demo_qa.sh
```

脚本会：

1. 调用 `http://localhost:8000/healthz` 判定 FastAPI 是否在线（未运行则提示执行 `./start_api.sh`）
2. 自动在浏览器打开 `frontend/qa_chat_demo.html`
3. 询问是否使用命令行交互，若确认则执行 `python relative_tests/test_qa.py --interactive`

### 手动使用 Web 界面

1. 确保 API 运行（`curl http://localhost:8000/healthz` 不报错即可）
2. 浏览器直接打开 `frontend/qa_chat_demo.html`（`open`/`xdg-open`/双击均可）
3. 在页面顶部选择 **示范园区综合能源规划 (demo-park)** 场景，界面会展示欢迎语与 4 个建议问题
4. 通过点击建议问题或在输入框中键入问题开始对话

推荐问题（页面会自动列出，可直接点击）：

- 有哪些推荐的减排措施？
- 园区的基线排放是多少？
- 有哪些政策支持和补贴？
- 屋顶光伏的具体情况如何？

界面特性：聊天式 UI、实时加载动画、回答附带置信度与信息来源（措施 / 政策 / 数据缺口）。

### 故障排查

- 页面提示“无法加载场景”：先运行 `./start_api.sh` 或至少保证 `curl http://localhost:8000/healthz` 正常
- 提问无响应：打开开发者工具 (F12) 检查网络/CORS；确认 `outputs/demo-park` 下的报告与 `qa_index.json` 存在，可通过运行 `python -m multi_energy_agent.runner` 重新生成
- 建议问题缺失：确认已选择场景，必要时重新生成报告
- 快速检测 API 端点：执行 `./relative_tests/test_web_api.sh`（依次请求健康检查、建议问题、问答接口）

通过以上内容即可在 README 中直接了解如何启动后端、验证 API、以及使用 Web/CLI 问答界面，避免反复查阅分散文档。


