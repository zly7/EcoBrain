# FastAPI 接口使用指南

## 概述

multi_energy_agent 提供了完整的 FastAPI REST 接口和 WebSocket 实时推送功能，可以将多智能体分析流水线作为服务使用。

## 架构说明

### 核心组件

1. **main.py** - FastAPI 应用主入口
   - 定义所有 REST 端点
   - 管理 WebSocket 连接
   - 协调后台任务执行

2. **models.py** - Pydantic 数据模型
   - `ScenarioRequest` - 场景创建请求
   - `ScenarioStatus` - 运行状态枚举
   - `ScenarioEvent` - 事件模型
   - `ScenarioDetailResponse` - 详情响应

3. **service.py** - 后台执行服务
   - `ScenarioExecutor` - 异步执行 Agent 流水线
   - `ScenarioEventPublisher` - 发布进度事件

4. **store.py** - 内存存储
   - `ScenarioRunStore` - 线程安全的运行记录存储
   - `ScenarioRun` - 运行记录数据类

5. **websocket.py** - WebSocket 管理
   - `WebSocketManager` - 管理客户端连接和消息广播

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn
```

### 2. 启动服务

**方式一：使用启动脚本**
```bash
./start_api.sh
```

**方式二：直接使用 uvicorn**
```bash
uvicorn multi_energy_agent.api.main:app --reload --host 0.0.0.0 --port 8000
```

**方式三：Python 模块方式**
```bash
python -m uvicorn multi_energy_agent.api.main:app --reload
```

### 3. 访问文档

启动后访问以下地址：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/healthz

## API 端点详解

### 1. 健康检查

```http
GET /healthz
```

**响应示例：**
```json
{
  "status": "ok",
  "stages": "intake,insight,report"
}
```

### 2. 创建场景运行

```http
POST /api/v1/scenarios
Content-Type: application/json
```

**请求体：**
```json
{
  "selection": {
    "metadata": {
      "admin_code": "320500",
      "area_km2": 15.3,
      "entity_count": 3,
      "industry_codes": ["C26", "C30", "C34"],
      "roof_area_m2": 90000,
      "solar_profile": "available",
      "waste_heat_profile": "available",
      "steam_grade": "medium_pressure",
      "load_profile": "available",
      "tou_tariff": "available",
      "motor_inventory": "available",
      "operating_hours": 7200
    }
  },
  "scenario": {
    "scenario_id": "my-park-001",
    "baseline_year": 2023,
    "electricity_price": 0.82,
    "carbon_price": 50.0
  },
  "inputs": {
    "csv_paths": [
      "multi_energy_agent/data/mock_sources/roof_inventory.csv",
      "multi_energy_agent/data/mock_sources/enterprise_registry.csv"
    ],
    "pdf_paths": [
      "multi_energy_agent/data/mock_sources/policy_brief.txt"
    ],
    "excel_paths": [
      "multi_energy_agent/data/mock_sources/cashflow_analysis.csv"
    ]
  },
  "output_root": "outputs"
}
```

**响应示例：**
```json
{
  "run_id": "a1b2c3d4e5f6...",
  "scenario_id": "my-park-001",
  "status": "pending",
  "created_at": "2026-01-22T12:00:00Z"
}
```

### 3. 列出所有场景

```http
GET /api/v1/scenarios
```

**响应示例：**
```json
[
  {
    "run_id": "a1b2c3d4e5f6...",
    "scenario_id": "my-park-001",
    "status": "completed",
    "created_at": "2026-01-22T12:00:00Z",
    "updated_at": "2026-01-22T12:05:00Z"
  }
]
```

### 4. 获取场景详情

```http
GET /api/v1/scenarios/{run_id}
```

**响应示例：**
```json
{
  "run_id": "a1b2c3d4e5f6...",
  "scenario_id": "my-park-001",
  "status": "completed",
  "created_at": "2026-01-22T12:00:00Z",
  "updated_at": "2026-01-22T12:05:00Z",
  "selection": { ... },
  "scenario": { ... },
  "inputs": { ... },
  "events": [
    {
      "event_id": "evt001",
      "run_id": "a1b2c3d4e5f6...",
      "event": "run_started",
      "created_at": "2026-01-22T12:00:00Z",
      "stage": null,
      "message": "Scenario execution started",
      "payload": {}
    },
    {
      "event_id": "evt002",
      "run_id": "a1b2c3d4e5f6...",
      "event": "stage_started",
      "created_at": "2026-01-22T12:00:01Z",
      "stage": "intake",
      "message": "intake stage started",
      "payload": {}
    }
  ],
  "result": {
    "envelopes": {
      "intake": { ... },
      "insight": { ... },
      "report": {
        "artifacts": {
          "report_path": "outputs/my-park-001/report.md"
        }
      }
    }
  },
  "error": null
}
```

### 5. WebSocket 实时订阅

```
ws://localhost:8000/ws/scenarios/{run_id}
```

**接收的消息格式：**
```json
{
  "event_id": "evt003",
  "run_id": "a1b2c3d4e5f6...",
  "event": "stage_completed",
  "created_at": "2026-01-22T12:02:00Z",
  "stage": "intake",
  "message": "intake stage completed",
  "payload": {
    "result_id": "res001",
    "metrics_count": 5,
    "review_items": 2
  }
}
```

### 6. 报告问答 - 提问

```http
POST /api/v1/scenarios/{scenario_id}/qa?question={question}
```

**参数：**
- `scenario_id`: 场景ID（必须是已完成的场景）
- `question`: 问题内容（URL编码）

**响应示例：**
```json
{
  "answer": "根据报告分析，推荐以下措施：\n\n1. 屋顶光伏 (评分: 0.77)\n   - 预期减排：3.77 tCO2\n   - 投资额：0.06 百万元\n\n2. 高效电机改造 (评分: 0.66)\n   - 预期减排：1.89 tCO2\n   - 投资额：0.03 百万元",
  "sources": [
    {
      "type": "measure",
      "id": "PV_ROOF",
      "name": "屋顶光伏"
    },
    {
      "type": "measure",
      "id": "EE_MOTOR",
      "name": "高效电机与变频改造"
    }
  ],
  "confidence": 0.8,
  "relevant_sections": 3
}
```

### 7. 报告问答 - 获取建议问题

```http
GET /api/v1/scenarios/{scenario_id}/qa/suggestions
```

**响应示例：**
```json
{
  "scenario_id": "demo-park",
  "suggestions": [
    "有哪些推荐的减排措施？",
    "园区的基线排放是多少？",
    "有哪些政策支持和补贴？",
    "屋顶光伏的具体情况如何？",
    "还需要补充哪些数据？"
  ]
}
```

## 事件类型

### 运行级别事件
- `run_started` - 场景开始执行
- `run_completed` - 场景执行完成
- `run_failed` - 场景执行失败

### 阶段级别事件
- `stage_started` - 某个阶段开始
- `stage_completed` - 某个阶段完成

### 阶段名称
- `intake` - 数据接入阶段
- `insight` - 洞察分析阶段
- `report` - 报告生成阶段

## 使用示例

### Python 客户端示例

```python
import requests
import json

# 1. 创建场景
response = requests.post(
    "http://localhost:8000/api/v1/scenarios",
    json={
        "selection": {"metadata": {"admin_code": "320500"}},
        "scenario": {"scenario_id": "test-001", "baseline_year": 2023},
        "inputs": {"csv_paths": [], "pdf_paths": [], "excel_paths": []}
    }
)
run_id = response.json()["run_id"]
print(f"创建运行: {run_id}")

# 2. 轮询状态
import time
while True:
    response = requests.get(f"http://localhost:8000/api/v1/scenarios/{run_id}")
    status = response.json()["status"]
    print(f"当前状态: {status}")
    if status in ["completed", "failed"]:
        break
    time.sleep(2)

# 3. 获取结果
response = requests.get(f"http://localhost:8000/api/v1/scenarios/{run_id}")
result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
```

### JavaScript/WebSocket 示例

```javascript
// 创建场景
const response = await fetch('http://localhost:8000/api/v1/scenarios', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    selection: { metadata: { admin_code: '320500' } },
    scenario: { scenario_id: 'test-001', baseline_year: 2023 },
    inputs: { csv_paths: [], pdf_paths: [], excel_paths: [] }
  })
});
const { run_id } = await response.json();

// 订阅 WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/scenarios/${run_id}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`[${data.event}] ${data.message}`);
  
  if (data.event === 'run_completed') {
    console.log('报告路径:', data.payload.report_path);
    ws.close();
  }
};

ws.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};
```

### 报告问答示例

```javascript
// 获取建议问题
const suggestionsResponse = await fetch(
  'http://localhost:8000/api/v1/scenarios/demo-park/qa/suggestions'
);
const { suggestions } = await suggestionsResponse.json();
console.log('建议问题:', suggestions);

// 提问
const question = '有哪些推荐的减排措施？';
const qaResponse = await fetch(
  `http://localhost:8000/api/v1/scenarios/demo-park/qa?question=${encodeURIComponent(question)}`,
  { method: 'POST' }
);
const result = await qaResponse.json();

console.log('回答:', result.answer);
console.log('置信度:', result.confidence);
console.log('信息来源:', result.sources);
```

### cURL 示例

```bash
# 创建场景
curl -X POST http://localhost:8000/api/v1/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "selection": {"metadata": {"admin_code": "320500"}},
    "scenario": {"scenario_id": "test-001", "baseline_year": 2023},
    "inputs": {"csv_paths": [], "pdf_paths": [], "excel_paths": []}
  }'

# 获取详情
curl http://localhost:8000/api/v1/scenarios/{run_id}

# 列出所有场景
curl http://localhost:8000/api/v1/scenarios
```

## 测试脚本

项目提供了完整的测试脚本 `test_api.py`：

```bash
# 确保 API 服务正在运行
./start_api.sh

# 在另一个终端运行测试
python test_api.py
```

测试脚本会：
1. 检查健康状态
2. 创建新场景
3. 监控执行进度
4. 获取最终结果
5. 列出所有场景

## 状态流转

```
pending → running → completed
                 ↘ failed
```

- **pending**: 场景已创建，等待执行
- **running**: 正在执行 Agent 流水线
- **completed**: 执行成功完成
- **failed**: 执行过程中出错

## 注意事项

1. **内存存储**: 当前使用内存存储，服务重启后数据会丢失。生产环境建议使用数据库。

2. **并发处理**: 支持多个场景并发执行，每个场景在独立的后台任务中运行。

3. **文件路径**: `inputs` 中的文件路径需要是服务器可访问的绝对路径或相对路径。

4. **WebSocket 连接**: 客户端需要保持连接才能接收实时事件，断开后不会重新发送历史事件。

5. **错误处理**: 如果 Agent 执行失败，状态会变为 `failed`，错误信息会记录在 `error` 字段。

## 扩展建议

### 持久化存储
将 `ScenarioRunStore` 替换为数据库实现（如 PostgreSQL、MongoDB）：

```python
# 示例：使用 SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class DatabaseScenarioRunStore(ScenarioRunStore):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
    
    def create_run(self, request: ScenarioRequest) -> ScenarioRun:
        # 保存到数据库
        pass
```

### 认证授权
添加 JWT 或 OAuth2 认证：

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/api/v1/scenarios")
async def create_scenario(
    request: ScenarioRequest,
    token: str = Depends(oauth2_scheme)
):
    # 验证 token
    pass
```

### 任务队列
使用 Celery 或 RQ 处理长时间运行的任务：

```python
from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379')

@celery_app.task
def execute_scenario(run_id: str):
    # 执行场景
    pass
```

## 故障排查

### 服务无法启动
- 检查端口 8000 是否被占用
- 确认已安装 `fastapi` 和 `uvicorn`
- 查看错误日志

### WebSocket 连接失败
- 确认使用 `ws://` 协议（非 HTTPS 环境）
- 检查防火墙设置
- 验证 run_id 是否正确

### 场景执行失败
- 查看 `error` 字段获取详细错误信息
- 检查输入文件路径是否正确
- 确认 `scenario_id` 已提供

## 相关文档

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Uvicorn 文档](https://www.uvicorn.org/)
- [WebSocket 协议](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
