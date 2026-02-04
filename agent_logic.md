# EcoBrain 多能源园区低碳规划系统 - 调用逻辑

## 系统架构概览

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    API 层 (FastAPI)                          │
│                    main.py                                   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                  场景执行器 (ScenarioExecutor)               │
│                    service.py                                │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent 管道                                │
│  DataIntakeAgent → InsightSynthesisAgent → ReportAgent      │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    工具层 (Tools)                            │
│  FHD | LYX | EcoKG | PDF                                    │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    输出文件                                  │
│  report.md | report.pdf | artifacts/                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 完整调用流程

### 第一阶段：API 入口

**文件**: `multi_energy_agent/api/main.py`

```
POST /api/v1/scenarios
    │
    ├── 创建场景运行记录 (store.create_run)
    │
    └── 异步调度执行 (_schedule_run)
            │
            └── asyncio.create_task(executor.run(run_id))
```

**关键端点**:
- `POST /api/v1/scenarios` - 创建并执行场景
- `GET /api/v1/scenarios/{run_id}` - 获取场景状态
- `POST /api/v1/chat` - 对话式交互 (ChatAgent)

---

### 第二阶段：场景执行

**文件**: `multi_energy_agent/api/service.py`

```python
ScenarioExecutor.run(run_id):
    │
    ├── 1. 初始化运行上下文
    │       run_ctx = init_run_context(scenario_id, output_dir)
    │       # 创建日志文件:
    │       #   - log/running_log/<timestamp>_<scenario_id>.log
    │       #   - log/direct_llm_log/<timestamp>_<scenario_id>.jsonl
    │
    ├── 2. 初始化工具注册表
    │       tools = default_tool_registry()
    │       # 注册工具:
    │       #   - load_fhd_back_data
    │       #   - load_lyx_energy_scores
    │       #   - materialize_eco_knowledge_graph
    │       #   - query_eco_knowledge_graph
    │       #   - render_pdf_report
    │
    ├── 3. 初始化 LLM 客户端
    │       llm = StructuredLLMClient(run_context=run_ctx)
    │
    ├── 4. 构建初始状态
    │       state = {
    │           "selection": {...},      # 用户选择的园区/地区
    │           "scenario": {...},       # 场景配置
    │           "inputs": {...},         # 用户输入
    │           "output_dir": "...",     # 输出目录
    │           "run_context": run_ctx,  # 运行上下文
    │           "tools": tools,          # 工具注册表
    │           "envelopes": {},         # 各阶段结果
    │           "review_items": [],      # 人工审核项
    │       }
    │
    └── 5. 执行 Agent 管道
            pipeline = [
                DataIntakeAgent(llm=llm),
                InsightSynthesisAgent(llm=llm),
                ReportOrchestratorAgent(llm=llm),
            ]
            for agent in pipeline:
                result = agent.run(state)
                state["envelopes"][stage] = result.envelope
```

---

### 第三阶段：Agent 管道执行

#### Stage 1: DataIntakeAgent (数据接入)

**文件**: `multi_energy_agent/agents/data_intake.py`

```
DataIntakeAgent.run(state):
    │
    ├── T1: 加载 FHD 园区数据
    │       tools.call("load_fhd_back_data", {
    │           output_dir, filters, max_matched_rows=5000,
    │           include_aoi_summary=True
    │       })
    │       │
    │       └── [FHD] Loading Excel file: 产业园区网_产业园数据.xlsx (22.4MB)
    │           [FHD] Processed 20000 rows...
    │           [FHD] Processed 40000 rows...
    │           ...
    │           [FHD] Completed: 104127 total rows, X matched
    │           │
    │           └── [FHD-AOI] Loading shapefile: 产业园AOI.shp (75.5MB)
    │               [FHD-AOI] Iterating features...
    │               [FHD-AOI] Completed: X features, Y matched
    │
    ├── T2: 加载 LYX 能源评分数据
    │       tools.call("load_lyx_energy_scores", {
    │           output_dir, industry_keywords, industry_weights
    │       })
    │       │
    │       └── [LYX] Loading score table: 能源评分表.csv
    │           [LYX] Score table loaded, X rows
    │           [LYX] Completed: X keywords processed
    │
    ├── T3: 构建 EcoKG 语料库
    │       tools.call("materialize_eco_knowledge_graph", {
    │           output_dir, chunk_size=600, chunk_overlap=120
    │       })
    │       │
    │       └── [EcoKG] Found X files to process
    │           [EcoKG] Processing file 1/X: policy.pdf
    │           [EcoKG] Processing file 2/X: ...
    │           [EcoKG] Completed: X files, Y chunks
    │
    └── 输出: ResultEnvelope(stage=INTAKE, metrics={...}, artifacts={...})
```

**输出文件**:
- `outputs/<scenario_id>/artifacts/fhd_matched_parks.csv`
- `outputs/<scenario_id>/artifacts/fhd_summary.json`
- `outputs/<scenario_id>/artifacts/fhd_aoi_summary.json`
- `outputs/<scenario_id>/artifacts/lyx_energy_tendency.json`
- `outputs/<scenario_id>/artifacts/eco_kg_corpus.jsonl`

---

#### Stage 2: InsightSynthesisAgent (洞察合成)

**文件**: `multi_energy_agent/agents/insight.py`

```
InsightSynthesisAgent.run(state):
    │
    ├── T4: 构建园区画像 (park_profile)
    │       - 从 FHD 数据提取: 产业分布、级别分布、地理位置
    │       - 计算: matched_parks, total_parks, top_industries
    │
    ├── T5: 推断能源倾向 (energy_tendency)
    │       - 从 LYX 数据提取: 能源维度评分
    │       - 计算: energy_mix, priorities, suggestions
    │
    ├── T6: 筛选适用措施 (measures)
    │       - 基于能源倾向匹配措施库
    │       - 计算: applicability_score, expected_reduction
    │
    ├── T7: 查询政策知识图谱
    │       tools.call("query_eco_knowledge_graph", {
    │           output_dir, query="...", top_k=6
    │       })
    │       │
    │       └── [EcoKG] Query: 光伏补贴政策...
    │           [EcoKG] Building vector index...
    │           [EcoKG] Index built, X items
    │           [EcoKG] Query completed: X snippets found
    │
    └── 输出: ResultEnvelope(stage=INSIGHT, metrics={...}, artifacts={
            park_profile, energy_tendency, measures, eco_kg_evidence
        })
```

**输出文件**:
- `outputs/<scenario_id>/artifacts/insight_summary.json`

---

#### Stage 3: ReportOrchestratorAgent (报告生成)

**文件**: `multi_energy_agent/agents/report.py`

```
ReportOrchestratorAgent.run(state):
    │
    ├── T8: 准备报告数据
    │       - 收集: park_profile, energy_tendency, measures, eco_kg_evidence
    │       - 构建: system_prompt, user_prompt, fallback
    │
    ├── T9: 调用 LLM 生成报告
    │       llm.markdown(system_prompt, user_prompt, fallback)
    │       │
    │       └── [LLM] Calling mimo-v2-flash (max_tokens=4000)...
    │           [LLM] Response received, length: XXXX chars
    │
    ├── T10: 保存 Markdown 报告
    │       report.md → outputs/<scenario_id>/report.md
    │
    ├── T11: 渲染 PDF 报告
    │       tools.call("render_pdf_report", {
    │           markdown_path, pdf_path, title
    │       })
    │       │
    │       └── [PDF] Rendering PDF from: report.md
    │           [PDF] Markdown loaded, XXXX chars
    │           [PDF] Trying WeasyPrint...
    │           [PDF] WeasyPrint succeeded: report.pdf
    │
    └── 输出: ResultEnvelope(stage=REPORT, metrics={...}, artifacts={
            report_path, report_pdf_path
        })
```

**输出文件**:
- `outputs/<scenario_id>/report.md`
- `multi_energy_agent/pdf/<timestamp>_<scenario_id>.pdf`
- `outputs/<scenario_id>/artifacts/qa_index.json`

---

## 工具详情

### 1. load_fhd_back_data (FHD 园区数据)

**数据文件**:
- `other_back_data/fhd/产业园区网_产业园数据.xlsx` (22.4 MB, 10万+园区)
- `other_back_data/fhd/产业园AOI.shp` (75.5 MB, 地理边界)

**功能**: 加载并过滤园区数据，生成统计摘要

**耗时**: 首次加载约 30-60 秒

---

### 2. load_lyx_energy_scores (LYX 能源评分)

**数据文件**:
- `other_back_data/lyx/*.csv` (能源评分表)

**功能**: 根据产业关键词匹配能源需求倾向

**耗时**: 约 1-2 秒

---

### 3. materialize_eco_knowledge_graph (EcoKG 构建)

**数据文件**:
- `eco_knowledge_graph/data/*.pdf` (政策文档)
- `eco_knowledge_graph/data/*.docx` (政策文档)

**功能**: 将政策文档切分为语料块，构建检索索引

**耗时**: 取决于文档数量，约 5-30 秒

---

### 4. query_eco_knowledge_graph (EcoKG 查询)

**功能**: 基于 TF-IDF 向量检索相关政策片段

**耗时**: 约 1-2 秒

---

### 5. render_pdf_report (PDF 渲染)

**引擎**: WeasyPrint (优先) 或 ReportLab (备选)

**功能**: 将 Markdown 报告渲染为 PDF

**耗时**: 约 5-15 秒

---

## LLM 调用点

| 位置 | 用途 | 文件 |
|------|------|------|
| ChatAgent._analyze_intent | 意图识别 | chat_agent.py:114 |
| ReportAgent._render_markdown_with_llm | 报告生成 | report.py:546 |
| DataIntakeAgent (可选) | 数据描述 | data_intake.py:477 |
| ReportQAService._generate_llm_answer | 问答服务 | qa.py:223 |

---

## 日志输出

### 命令行日志标签

| 标签 | 来源 |
|------|------|
| `[ChatAgent]` | 对话 Agent |
| `[FHD]` | FHD 园区数据加载 |
| `[FHD-AOI]` | FHD AOI 地理数据加载 |
| `[LYX]` | LYX 能源评分加载 |
| `[EcoKG]` | 知识图谱构建/查询 |
| `[LLM]` | LLM API 调用 |
| `[PDF]` | PDF 渲染 |
| `[ReportQAService]` | 问答服务 |

### 日志文件

- **运行日志**: `multi_energy_agent/log/running_log/<timestamp>_<scenario_id>.log`
- **LLM 日志**: `multi_energy_agent/log/direct_llm_log/<timestamp>_<scenario_id>.jsonl`

---

## 输出目录结构

```
outputs/<scenario_id>/
├── report.md                          # Markdown 报告
├── plan.md                            # 执行计划
└── artifacts/
    ├── fhd_matched_parks.csv          # 匹配的园区列表
    ├── fhd_summary.json               # FHD 统计摘要
    ├── fhd_aoi_summary.json           # AOI 地理摘要
    ├── lyx_energy_tendency.json       # 能源倾向分析
    ├── eco_kg_corpus.jsonl            # 知识图谱语料
    ├── insight_summary.json           # 洞察摘要
    └── qa_index.json                  # 问答索引

multi_energy_agent/pdf/
└── <timestamp>_<scenario_id>.pdf      # PDF 报告
```

---

## 典型执行时间线

```
0s    ─── 请求到达 API
      │
1s    ─── DataIntakeAgent 开始
      │   ├── [FHD] 加载 Excel (30-60s)
      │   ├── [FHD-AOI] 加载 Shapefile (10-20s)
      │   ├── [LYX] 加载评分表 (1-2s)
      │   └── [EcoKG] 构建语料库 (5-30s)
      │
60s   ─── InsightSynthesisAgent 开始
      │   ├── 构建园区画像 (<1s)
      │   ├── 推断能源倾向 (<1s)
      │   ├── 筛选措施 (<1s)
      │   └── [EcoKG] 查询政策 (1-2s)
      │
65s   ─── ReportOrchestratorAgent 开始
      │   ├── [LLM] 生成报告 (10-30s)
      │   └── [PDF] 渲染 PDF (5-15s)
      │
90s   ─── 完成
```

**总耗时**: 约 60-120 秒（首次运行，取决于数据量和 LLM 响应速度）
