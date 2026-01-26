# energy_llm

知识图谱与多智能体流水线的内部联调仓库。`knowledge_graph` 负责生成调试用的 mock 数据与集成 KG，`multi_energy_agent` 读取输出的 `mock_policy_kg.json` 等文件完成政策+财务评估。

## 🚀 快速开始

### 方式一：命令行运行

1. **生成 mock 数据与知识图谱**  
   ```bash
   python -m knowledge_graph.build_mock_kg
   ```  
   - 会调用 `knowledge_graph.mock_sources` 写出 `data/mock_sources/*`  
   - 构建园区+政策 KG，输出：  
     - `multi_energy_agent/data/mock_policy_kg.json`（供 PolicyKnowledgeGraphAgent 使用）  
     - `multi_energy_agent/data/mock_park_policy_graph.json`（完整节点/边快照）

2. **执行多阶段 Agent 流水线**  
   ```bash
   python -m multi_energy_agent.runner --no-langgraph
   ```  
   - 若已安装 LangGraph，可去掉 `--no-langgraph` 使用图执行模式  
   - Runner 会自动读取生成的 `mock_policy_kg.json`，依次完成：
     - `geo` → `baseline` → `measures` → `policy` → `finance` → `report`
   - 最终报告保存在 `outputs/demo-park/report.md`

### 方式二：FastAPI 服务

1. **启动 API 服务**
   ```bash
   ./start_api.sh
   # 或
   uvicorn multi_energy_agent.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **访问 API 文档**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - 健康检查: http://localhost:8000/healthz

3. **测试 API**
   ```bash
   python test_api.py
   # 或在浏览器打开
   open api_client_demo.html
   ```

4. **使用问答功能**
   ```bash
   # 在浏览器打开问答界面
   open qa_chat_demo.html
   
   # 或使用命令行测试
   python test_qa.py
   python test_qa.py --interactive  # 交互式模式
   ```

## 📁 项目结构

```
energy_llm/
├── knowledge_graph/              # 知识图谱构建模块
│   ├── build_kg.py              # KG 构建主逻辑
│   ├── build_mock_kg.py         # Mock 数据 + KG 生成
│   ├── kg_model.py              # KG 数据模型
│   └── mock_sources.py          # Mock 数据源生成器
│
├── multi_energy_agent/           # 多智能体分析模块
│   ├── agents/                  # Agent 实现
│   │   ├── base.py             # 基础 Agent 类
│   │   ├── baseline.py         # 基线分析
│   │   ├── data_intake.py      # 数据接入
│   │   ├── finance.py          # 财务分析
│   │   ├── geo.py              # 地理解析
│   │   ├── insight.py          # 洞察综合
│   │   ├── measures.py         # 措施筛选
│   │   ├── policy.py           # 政策匹配
│   │   └── report.py           # 报告生成
│   │
│   ├── api/                     # FastAPI 接口
│   │   ├── main.py             # API 主入口
│   │   ├── models.py           # 数据模型
│   │   ├── service.py          # 后台服务
│   │   ├── store.py            # 存储管理
│   │   └── websocket.py        # WebSocket 管理
│   │
│   ├── data/                    # 数据目录
│   │   └── mock_sources/       # Mock 数据文件
│   │       ├── roof_inventory.csv
│   │       ├── enterprise_registry.csv
│   │       ├── enterprise_energy_monthly_2023.csv
│   │       ├── solar_profile.csv
│   │       ├── waste_heat_profile.csv
│   │       ├── load_profile.csv
│   │       ├── motor_inventory.csv
│   │       ├── tou_tariff.csv
│   │       ├── cashflow_analysis.csv
│   │       ├── energy_flow_analysis.csv
│   │       └── policy_brief.txt
│   │
│   ├── graph.py                 # LangGraph 流水线
│   ├── llm.py                   # LLM 客户端
│   ├── planning.py              # 计划管理
│   ├── policy_kg.py             # 政策 KG 接口
│   ├── runner.py                # 命令行运行器
│   └── schemas.py               # 数据模式定义
│
├── outputs/                      # 输出目录
│   └── demo-park/               # 场景输出
│       ├── report.md            # 最终报告
│       ├── plan.md              # 任务计划
│       └── artifacts/           # 中间产物
│
├── test_api.py                  # API 测试脚本
├── test_qa.py                   # 问答功能测试脚本
├── api_client_demo.html         # HTML 客户端演示
├── qa_chat_demo.html            # 问答聊天界面
├── start_api.sh                 # API 启动脚本
├── API使用指南.md               # API 详细文档
├── FastAPI接口总结.md           # API 架构总结
└── 报告问答功能说明.md          # 问答功能说明
```

## 📊 数据完备性

当前 mock 数据包含：

### 基础数据
- ✅ 屋顶清单（4栋建筑，90,000㎡）
- ✅ 企业注册信息（3家企业）
- ✅ 月度能耗数据（2023年全年）
- ✅ 行业能耗标准

### 措施相关数据
- ✅ 光伏潜力分析（solar_profile.csv）
- ✅ 余热源详情（waste_heat_profile.csv）
- ✅ 负荷曲线（load_profile.csv，72小时数据）
- ✅ 电机清单（motor_inventory.csv，35台设备）
- ✅ 分时电价（tou_tariff.csv）

### 分析数据
- ✅ 现金流分析（cashflow_analysis.csv）
- ✅ 能流分析（energy_flow_analysis.csv）
- ✅ 政策文件（policy_brief.txt）

### 知识图谱
- ✅ 政策知识图谱（mock_policy_kg.json）
- ✅ 完整图谱快照（mock_park_policy_graph.json）

## 📈 运行结果

### 报告指标
- **数据完备度**: 1.0
- **CSV文件数**: 11个
- **PDF文件数**: 1个
- **Excel文件数**: 1个
- **报告字数**: 1889字（中文字符）
- **主要数据缺口**: 仅2个中等优先级缺口

### 措施评分
| 措施 | 评分 | 减排量 (tCO2) | CAPEX (百万) | 年收益 (百万) |
|------|------|---------------|--------------|---------------|
| 屋顶光伏 | 0.77 | 3.77 | 0.06 | 4.08 |
| 高效电机改造 | 0.66 | 1.89 | 0.03 | 2.04 |
| 余热回收+热泵 | 0.65 | 2.51 | 0.04 | 2.72 |
| 储能削峰填谷 | 0.63 | 1.47 | 0.02 | 1.59 |

### 政策匹配
- 匹配条款数: 4条
- 涵盖措施: 光伏、余热、电机、储能
- 补贴比例: 8%-15%

## 🔧 环境配置

### 可选环境变量

```bash
# LLM 配置（可选，用于报告增强）
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_TEMPERATURE="0.2"

# 政策知识图谱路径（可选）
export POLICY_KG_PATH="path/to/policy_kg.json"
```

### 依赖安装

```bash
# 基础依赖
pip install pandas openpyxl pypdf

# API 服务依赖
pip install fastapi uvicorn

# LangGraph 支持（可选）
pip install langgraph
```

## 📚 文档

- [API使用指南.md](./API使用指南.md) - FastAPI 接口详细使用说明
- [FastAPI接口总结.md](./FastAPI接口总结.md) - API 架构和设计总结
- [报告问答功能说明.md](./报告问答功能说明.md) - 智能问答功能详解
- [multi_energy_agent/README.md](./multi_energy_agent/README.md) - Agent 模块说明
- [multi_energy_agent/api/README.md](./multi_energy_agent/api/README.md) - API 快速入门

## 🧪 测试

### 命令行测试
```bash
# 生成数据并运行
python -m knowledge_graph.build_mock_kg
python -m multi_energy_agent.runner --no-langgraph

# 查看报告
cat outputs/demo-park/report.md
```

### API 测试
```bash
# 启动服务
./start_api.sh

# 运行测试脚本（另一个终端）
python test_api.py

# 或使用浏览器打开 HTML 客户端
open api_client_demo.html
```

## 🎯 核心特性

### 多智能体流水线
- ✅ 数据接入 (DataIntakeAgent)
- ✅ 地理解析 (GeoResolverAgent)
- ✅ 基线分析 (BaselineAgent)
- ✅ 措施筛选 (MeasureScreenerAgent)
- ✅ 政策匹配 (PolicyKnowledgeGraphAgent)
- ✅ 财务整合 (FinanceIntegratorAgent)
- ✅ 报告生成 (ReportOrchestratorAgent)

### FastAPI 接口
- ✅ REST API（创建、查询、列出场景）
- ✅ WebSocket 实时推送
- ✅ 异步后台执行
- ✅ 自动 API 文档（Swagger/ReDoc）
- ✅ 线程安全存储
- ✅ 报告智能问答（Q&A）

### 知识图谱
- ✅ 政策条款匹配
- ✅ 补贴计算
- ✅ 行业代码过滤
- ✅ 地区代码匹配

## 🔄 工作流程

```
1. Mock数据生成
   ↓
2. 知识图谱构建
   ↓
3. Agent流水线执行
   ├─ 数据接入
   ├─ 基线分析
   ├─ 措施筛选
   ├─ 政策匹配
   ├─ 财务分析
   └─ 报告生成
   ↓
4. 输出报告和中间产物
```

## 🚧 注意事项

1. **目录名称**: 代码中已修复 `multi_enengy_agent` → `multi_energy_agent` 的拼写错误
2. **文件路径**: 确保所有输入文件路径正确且可访问
3. **内存存储**: API 服务使用内存存储，重启后数据会丢失（生产环境建议使用数据库）
4. **并发执行**: 支持多个场景并发运行

## 🔮 未来扩展

- [ ] 数据库持久化存储
- [ ] 用户认证和授权
- [ ] 任务队列（Celery/RQ）
- [ ] 缓存优化（Redis）
- [ ] 更多 Agent 类型
- [ ] 实时优化求解集成
- [ ] 前端可视化界面

## 📞 联系方式

如有问题或建议，请联系项目维护者。

---

**最后更新**: 2026-01-22  
**版本**: v0.2.0
