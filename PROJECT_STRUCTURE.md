# EcoBrain 项目结构

## 📁 目录结构

```
EcoBrain/
├── 📂 multi_energy_agent/          # 核心代码包
│   ├── __init__.py                 # 包初始化（导出 ChatAgent, run_scenario 等）
│   ├── runner.py                   # 主运行器（3 个 Agent 顺序执行）
│   ├── chat_agent.py               # 对话式 Agent（新增）
│   ├── llm.py                      # LLM 客户端封装
│   ├── planning.py                 # 任务计划管理
│   ├── schemas.py                  # 数据模式定义
│   │
│   ├── 📂 agents/                  # 三个核心 Agent
│   │   ├── base.py                 # Agent 基类
│   │   ├── data_intake.py          # Stage 1: 数据接入 + LLM 深度分析
│   │   ├── insight.py              # Stage 2: 洞察综合（确定性算法）
│   │   └── report.py               # Stage 3: 报告生成 + LLM 专业报告 + QA 索引
│   │
│   ├── 📂 api/                     # FastAPI Web 服务
│   │   ├── main.py                 # API 入口（包含对话端点）
│   │   ├── models.py               # 数据模型
│   │   ├── service.py              # 业务逻辑
│   │   ├── qa.py                   # 问答服务
│   │   ├── store.py                # 内存存储
│   │   ├── websocket.py            # WebSocket 管理
│   │   └── 📂 ts/                  # TypeScript 类型定义
│   │
│   ├── 📂 tools/                   # 工具注册表
│   │   ├── registry.py             # 工具注册中心
│   │   ├── back_data.py            # 后端数据工具（FHD/LYX/FDF）
│   │   ├── pdf_report.py           # PDF 报告工具
│   │   └── base.py                 # 工具基类
│   │
│   ├── 📂 reporting/               # 报告生成
│   │   └── pdf_weasyprint.py       # PDF 生成（WeasyPrint）
│   │
│   ├── 📂 utils/                   # 工具函数
│   │   └── logging.py              # 日志工具
│   │
│   └── 📂 data/                    # 内置数据
│       └── mock_*.json             # 模拟数据
│
├── 📂 other_back_data/             # 后端数据源（内置）
│   ├── 📂 fhd/                     # 产业园区数据（104,127 个）
│   │   ├── interface.py            # FHD 数据接口
│   │   └── *.xlsx, *.shp           # 园区名录 + 空间 AOI
│   ├── 📂 lyx/                     # 能源评分数据
│   │   ├── interface.py            # LYX 数据接口
│   │   └── gpt打分.csv             # 行业能源倾向评分
│   └── 📂 fdf/                     # 政策知识图谱接口
│       └── interface.py            # FDF 数据接口
│
├── 📂 eco_knowledge_graph/         # 政策知识图谱数据
│   └── 📂 data/                    # 21 个政策文档（.docx）
│       ├── 2025年能源工作指导意见.docx
│       ├── 关于开展零碳园区建设的通知.docx
│       └── ...
│
├── 📂 frontend/                    # 前端界面
│   ├── chat_interface.html         # 对话界面（新增）⭐
│   ├── api_client_demo.html        # API 客户端演示
│   └── qa_chat_demo.html           # QA 聊天演示
│
├── 📂 docs/                        # 项目文档
│   ├── 如何运行项目.md              # 运行指南
│   ├── 对话式Agent使用指南.md       # 对话 Agent 指南（新增）⭐
│   ├── 项目完整运作流程.md          # 完整流程说明
│   ├── 项目结构说明.md              # 代码结构说明
│   ├── FastAPI服务使用指南.md       # API 使用指南
│   ├── QA功能恢复完成.md            # QA 功能说明（新增）⭐
│   └── ...                         # 其他开发文档
│
├── 📂 outputs/                     # 输出结果（自动生成）
│   └── 📂 <scenario_id>/           # 场景输出目录
│       ├── plan.md                 # 任务执行日志
│       ├── report.md               # Markdown 报告
│       ├── report.pdf              # PDF 报告
│       └── 📂 artifacts/           # 中间产物
│           ├── inventory.json      # 数据清单
│           ├── qa_index.json       # QA 索引（新增）⭐
│           ├── csv_description_*.md    # CSV 深度分析
│           ├── fhd_matched_parks.csv   # 匹配的园区
│           ├── lyx_energy_tendency.json # 能源倾向
│           └── eco_kg_corpus.jsonl     # 政策检索结果
│
├── 📂 logs_llm_direct/             # LLM 调用日志（JSONL）
├── 📂 logs_running/                # 运行日志（文本）
├── 📂 relative_tests/              # 测试脚本
│
├── 📄 run_with_deepseek.sh         # DeepSeek 运行脚本
├── 📄 start_api.sh                 # API 启动脚本
├── 📄 chat_cli.py                  # 命令行对话脚本（新增）⭐
├── 📄 query_park.py                # 园区查询脚本（新增）⭐
├── 📄 check_project.py             # 项目检查脚本（新增）⭐
├── 📄 test_qa_restored.py          # QA 测试脚本（新增）⭐
├── 📄 run_custom_park.sh           # 自定义运行脚本（新增）
├── 📄 cleanup_project.sh           # 项目清理脚本
│
├── 📄 README.md                    # 项目说明
├── 📄 QUICKSTART.md                # 快速开始（新增）⭐
├── 📄 PROJECT_STRUCTURE.md         # 本文件（新增）⭐
└── 📄 .gitignore                   # Git 忽略配置
```

## 🎯 核心模块说明

### 1. multi_energy_agent/

**核心 Python 包**，包含所有业务逻辑。

#### 关键文件：
- `runner.py` - 主入口，协调 3 个 Agent 顺序执行
- `chat_agent.py` - 对话式 Agent，支持自然语言交互 ⭐
- `llm.py` - LLM 客户端，封装 OpenAI/DeepSeek API
- `__init__.py` - 导出 `ChatAgent`, `run_scenario` 等

#### 子模块：
- `agents/` - 三个核心 Agent（DataIntake, Insight, Report）
- `api/` - FastAPI Web 服务
- `tools/` - 工具注册表（FHD, LYX, FDF, PDF）
- `reporting/` - PDF 生成（WeasyPrint）
- `utils/` - 工具函数

### 2. other_back_data/

**内置数据源**，随项目一起分发：
- `fhd/` - 104,127 个产业园区数据
- `lyx/` - 行业能源倾向评分
- `fdf/` - 政策知识图谱接口

### 3. eco_knowledge_graph/

**政策文档原始数据**：
- 21 个 .docx 文件
- 在运行时解析为文本块并建立索引

### 4. frontend/

**前端界面**：
- `chat_interface.html` - 对话界面（新增）⭐
- `api_client_demo.html` - API 客户端演示
- `qa_chat_demo.html` - QA 聊天演示

### 5. docs/

**项目文档**，按主题分类：
- 运行指南
- 架构说明
- API 文档
- 优化记录

## 🚀 快速开始

### 方式 1：命令行对话（最简单）

```bash
python chat_cli.py
```

### 方式 2：Web 对话界面（最美观）

```bash
./start_api.sh
open frontend/chat_interface.html
```

### 方式 3：直接生成报告

```bash
./run_with_deepseek.sh
```

### 方式 4：自定义查询

```bash
python query_park.py --city 柳州 --industries 汽车,机械
```

## 🔍 项目检查

运行检查脚本验证项目配置：

```bash
python check_project.py
```

## 📊 数据流

```
用户输入
  ↓
[ChatAgent] 意图识别 → 参数提取
  ↓
[DataIntakeAgent] 数据接入 + LLM 深度分析
  ↓
[InsightSynthesisAgent] 园区画像 + 能源倾向 + 措施筛选
  ↓
[ReportOrchestratorAgent] LLM 专业报告 + PDF + QA 索引
  ↓
输出文件
  ├─ report.md
  ├─ report.pdf
  └─ artifacts/
      ├─ qa_index.json ⭐
      ├─ csv_description_*.md
      └─ ...
```

## 🆕 新增功能

### 1. 对话式 Agent ⭐

- **文件**: `multi_energy_agent/chat_agent.py`
- **功能**: 自然语言理解、意图识别、参数提取
- **使用**: `python chat_cli.py` 或 Web 界面

### 2. QA 索引生成 ⭐

- **文件**: `multi_energy_agent/agents/report.py`
- **功能**: 自动生成 `qa_index.json`，支持问答
- **包含**: 基线排放、措施详情、政策引用、数据缺口

### 3. Web 对话界面 ⭐

- **文件**: `frontend/chat_interface.html`
- **功能**: 美观的聊天界面，实时对话
- **特性**: 快捷建议、一键重置、响应式设计

### 4. 项目检查工具 ⭐

- **文件**: `check_project.py`
- **功能**: 验证项目结构、模块导入、环境配置
- **使用**: `python check_project.py`

## 📝 环境配置

### 必需环境变量

```bash
export DEEPSEEK_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-reasoner"
```

### 可选环境变量

```bash
export OPENAI_TEMPERATURE="1.0"
export OPENAI_MAX_TOKENS="8000"
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"  # macOS
```

## 🔗 模块导入路径

```python
# 核心功能
from multi_energy_agent import run_scenario, ChatAgent

# Agent
from multi_energy_agent.agents import DataIntakeAgent, InsightSynthesisAgent, ReportOrchestratorAgent

# LLM
from multi_energy_agent.llm import StructuredLLMClient

# API
from multi_energy_agent.api.main import app

# QA
from multi_energy_agent.api.qa import ReportQAService
```

## 📚 相关文档

- [README.md](README.md) - 项目说明
- [QUICKSTART.md](QUICKSTART.md) - 快速开始
- [docs/如何运行项目.md](docs/如何运行项目.md) - 详细运行指南
- [docs/对话式Agent使用指南.md](docs/对话式Agent使用指南.md) - 对话功能说明
- [docs/项目完整运作流程.md](docs/项目完整运作流程.md) - 系统架构
- [docs/FastAPI服务使用指南.md](docs/FastAPI服务使用指南.md) - API 文档

## ✅ 项目状态

- ✅ 核心功能完整
- ✅ 对话式 Agent 已实现
- ✅ QA 功能已恢复
- ✅ Web 界面已完成
- ✅ 文档已完善
- ✅ 所有检查通过

**项目已准备就绪，可以投入使用！**
