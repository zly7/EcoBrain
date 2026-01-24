# FastAPI 接口设置总结

## 📋 概述

multi_energy_agent 项目提供了完整的 FastAPI REST API 和 WebSocket 实时推送功能，可以将多智能体低碳分析流水线作为服务使用。

## 🏗️ 架构设计

### 核心文件结构

```
multi_energy_agent/api/
├── __init__.py
├── main.py          # FastAPI 应用主入口，定义所有端点
├── models.py        # Pydantic 数据模型（请求/响应）
├── service.py       # 后台执行服务（异步运行 Agent）
├── store.py         # 内存存储（线程安全）
├── websocket.py     # WebSocket 连接管理
└── README.md        # API 使用说明
```

### 技术栈

- **FastAPI**: 现代、高性能的 Web 框架
- **Uvicorn**: ASGI 服务器
- **Pydantic**: 数据验证和序列化
- **WebSocket**: 实时双向通信
- **asyncio**: 异步任务处理

## 🚀 快速启动

### 1. 安装依赖

```bash
pip install fastapi uvicorn
```

### 2. 启动服务

**方式一：使用启动脚本**
```bash
./start_api.sh
```

**方式二：直接命令**
```bash
uvicorn multi_energy_agent.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 访问文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/healthz

## 📡 API 端点

### REST API

| 方法 | 路径 | 功能 | 状态码 |
|------|------|------|--------|
| GET | `/healthz` | 健康检查 | 200 |
| POST | `/api/v1/scenarios` | 创建场景运行 | 201 |
| GET | `/api/v1/scenarios` | 列出所有场景 | 200 |
| GET | `/api/v1/scenarios/{run_id}` | 获取场景详情 | 200/404 |

### WebSocket

| 路径 | 功能 |
|------|------|
| `/ws/scenarios/{run_id}` | 订阅场景执行进度 |

## 🔄 工作流程

```
1. 客户端 POST /api/v1/scenarios
   ↓
2. 服务器创建 ScenarioRun 记录
   ↓
3. 后台启动异步任务执行 Agent 流水线
   ↓
4. 执行过程中发布事件到 WebSocket
   ↓
5. 客户端通过 WebSocket 接收实时进度
   ↓
6. 执行完成后更新状态和结果
   ↓
7. 客户端 GET /api/v1/scenarios/{run_id} 获取最终结果
```

## 📊 数据模型

### ScenarioRequest (输入)

```python
{
  "selection": {
    "metadata": {
      "admin_code": "320500",
      "area_km2": 15.3,
      "entity_count": 3,
      "industry_codes": ["C26", "C30", "C34"],
      "roof_area_m2": 90000,
      "solar_profile": "available",
      # ... 其他字段
    }
  },
  "scenario": {
    "scenario_id": "my-park-001",  # 必填
    "baseline_year": 2023,
    "electricity_price": 0.82,
    "carbon_price": 50.0
  },
  "inputs": {
    "csv_paths": ["path/to/file.csv"],
    "pdf_paths": ["path/to/doc.pdf"],
    "excel_paths": ["path/to/data.xlsx"]
  },
  "output_root": "outputs"
}
```

### ScenarioStatus (状态)

- `pending`: 等待执行
- `running`: 正在执行
- `completed`: 执行完成
- `failed`: 执行失败

### ScenarioEvent (事件)

```python
{
  "event_id": "evt001",
  "run_id": "a1b2c3d4...",
  "event": "stage_completed",
  "created_at": "2026-01-22T12:00:00Z",
  "stage": "intake",
  "message": "intake stage completed",
  "payload": {
    "result_id": "res001",
    "metrics_count": 5,
    "review_items": 2
  }
}
```

## 🎯 事件类型

### 运行级别
- `run_started` - 场景开始执行
- `run_completed` - 场景执行完成（payload 包含 report_path）
- `run_failed` - 场景执行失败（payload 包含 error）

### 阶段级别
- `stage_started` - 阶段开始（stage: intake/insight/report）
- `stage_completed` - 阶段完成（payload 包含 metrics_count 等）

## 💡 核心实现

### 1. 异步任务执行 (service.py)

```python
class ScenarioExecutor:
    async def run(self, run_id: str) -> None:
        # 在线程池中执行同步的 Agent 流水线
        loop = asyncio.get_running_loop()
        state = await loop.run_in_executor(None, self._execute_pipeline, run)
        
        # 发布事件
        self._publisher.emit(run_id, "run_completed", ...)
```

### 2. WebSocket 广播 (websocket.py)

```python
class WebSocketManager:
    def push(self, run_id: str, message: Dict[str, Any]) -> None:
        # 线程安全地向所有订阅者广播消息
        asyncio.run_coroutine_threadsafe(
            self._broadcast(run_id, message), 
            self._loop
        )
```

### 3. 线程安全存储 (store.py)

```python
class ScenarioRunStore:
    def __init__(self):
        self._runs: Dict[str, ScenarioRun] = {}
        self._lock = threading.Lock()
    
    def update_status(self, run_id: str, status: ScenarioStatus):
        with self._lock:
            run.status = status
            run.updated_at = utcnow()
```

## 🧪 测试工具

### 1. Python 测试脚本

```bash
python test_api.py
```

功能：
- 健康检查
- 创建场景
- 监控进度
- 获取结果
- 列出所有场景

### 2. HTML 客户端演示

```bash
# 在浏览器中打开
open api_client_demo.html
```

功能：
- 可视化控制面板
- 实时日志显示
- WebSocket 状态监控
- 场景列表管理

### 3. cURL 命令

```bash
# 创建场景
curl -X POST http://localhost:8000/api/v1/scenarios \
  -H "Content-Type: application/json" \
  -d @request.json

# 获取详情
curl http://localhost:8000/api/v1/scenarios/{run_id}
```

## 📝 使用示例

### Python 客户端

```python
import requests
import time

# 创建场景
response = requests.post(
    "http://localhost:8000/api/v1/scenarios",
    json={
        "selection": {"metadata": {"admin_code": "320500"}},
        "scenario": {"scenario_id": "test-001", "baseline_year": 2023},
        "inputs": {"csv_paths": [], "pdf_paths": [], "excel_paths": []}
    }
)
run_id = response.json()["run_id"]

# 轮询状态
while True:
    response = requests.get(f"http://localhost:8000/api/v1/scenarios/{run_id}")
    status = response.json()["status"]
    if status in ["completed", "failed"]:
        break
    time.sleep(2)

# 获取结果
result = response.json()
print(result["result"]["envelopes"]["report"]["artifacts"]["report_path"])
```

### JavaScript + WebSocket

```javascript
// 创建场景
const response = await fetch('http://localhost:8000/api/v1/scenarios', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ /* ... */ })
});
const { run_id } = await response.json();

// 订阅 WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/scenarios/${run_id}`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`[${data.event}] ${data.message}`);
  
  if (data.event === 'run_completed') {
    console.log('报告:', data.payload.report_path);
  }
};
```

## ⚙️ 配置选项

### Uvicorn 启动参数

```bash
uvicorn multi_energy_agent.api.main:app \
  --reload              # 开发模式，代码变更自动重载
  --host 0.0.0.0        # 监听所有网络接口
  --port 8000           # 端口号
  --workers 4           # 工作进程数（生产环境）
  --log-level info      # 日志级别
```

### 环境变量

```bash
# LLM 配置（可选）
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_TEMPERATURE="0.2"

# 政策知识图谱路径（可选）
export POLICY_KG_PATH="path/to/policy_kg.json"
```

## 🔒 安全建议

### 生产环境部署

1. **添加认证授权**
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

2. **使用 HTTPS**
```bash
uvicorn main:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

3. **限流保护**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/scenarios")
@limiter.limit("10/minute")
async def create_scenario(...):
    pass
```

4. **CORS 配置**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📈 性能优化

### 1. 使用数据库替代内存存储

```python
# 使用 PostgreSQL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql://user:pass@localhost/db")
Session = sessionmaker(bind=engine)
```

### 2. 使用任务队列

```python
# 使用 Celery
from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379')

@celery_app.task
def execute_scenario(run_id: str):
    # 执行场景
    pass
```

### 3. 添加缓存

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
```

## 🐛 故障排查

### 常见问题

1. **端口被占用**
```bash
# 查找占用端口的进程
lsof -i :8000
# 或
netstat -ano | grep 8000

# 杀死进程
kill -9 <PID>
```

2. **WebSocket 连接失败**
- 确认使用 `ws://` 协议（非 HTTPS）
- 检查防火墙设置
- 验证 run_id 正确

3. **场景执行失败**
- 查看 `error` 字段
- 检查文件路径
- 确认 `scenario_id` 已提供

4. **内存不足**
- 使用数据库存储
- 定期清理旧记录
- 增加服务器内存

## 📚 相关文档

- [API使用指南.md](./API使用指南.md) - 详细的 API 使用文档
- [test_api.py](./test_api.py) - Python 测试脚本
- [api_client_demo.html](./api_client_demo.html) - HTML 客户端演示
- [start_api.sh](./start_api.sh) - 服务启动脚本

## 🎉 总结

FastAPI 接口提供了：

✅ **完整的 REST API** - 创建、查询、列出场景  
✅ **实时 WebSocket** - 推送执行进度和事件  
✅ **异步执行** - 后台运行 Agent 流水线  
✅ **线程安全** - 支持并发请求  
✅ **自动文档** - Swagger UI 和 ReDoc  
✅ **易于测试** - 提供多种测试工具  
✅ **可扩展** - 支持认证、缓存、队列等扩展  

现在你可以将多智能体低碳分析系统作为微服务使用，轻松集成到前端应用或其他系统中！
