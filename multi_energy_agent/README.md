# multi_energy_agent 使用说明

本目录提供一个“报告优先”的园区能源/低碳分析 3-Agent 流水线：Intake → Insight → Report。各阶段通过统一的 BlackboardState 与 ResultEnvelope 传递结构化数据，便于证据追溯、人工复核与 UI/API 对接。

## 1. 目录结构

```
multi_energy_agent/
├── agents/
│   ├── data_intake.py         # DataIntakeAgent：CSV/PDF/Excel 接入与画像、plan.md 初始化/刷新
│   ├── insight.py             # InsightSynthesisAgent：基线描述、措施筛选、政策 KG 匹配、叙事汇总
│   └── report.py              # ReportOrchestratorAgent：生成 ≥1000 中文字符的 report.md + qa_index.json
├── planning.py                # PlanManager：Claude-code 风格 plan.md，内嵌 JSON 状态
├── policy_kg.py               # PolicyKnowledgeGraph：确定性匹配与补贴聚合（可替换为真实 KG 服务）
├── llm.py                     # StructuredLLMClient：可选的 LLM 文本增强（无 Key 走 fallback）
├── runner.py                  # run_scenario：顺序执行 3 个 Agent，返回 BlackboardState
├── schemas.py                 # Stage / ResultEnvelope / DataGap / ReviewItem 等共享结构
└── data/
    ├── mock_policy_kg.json    # 默认的政策 KG 示例数据
    └── mock_park_policy_graph.json
```

## 2. 环境要求

- Python 3.10+
- 可选依赖：
  - `pandas`（CSV 画像）、`openpyxl`（Excel 解析）、`pypdf` 或 `PyPDF2`（PDF 文本抽取）
  - `openai`（设置 `OPENAI_API_KEY` 后用于报告叙事增强）

无可选依赖或无 LLM Key 的情况下，系统仍可运行，缺失功能会以 DataGap 记录并采用降级回退。

## 3. 最小示例（Python 方式）

```python
from multi_energy_agent.runner import run_scenario

state = run_scenario(
    selection={
        "metadata": {
            "admin_code": "310000",
            "area_km2": 12.5,
            "entity_count": 18,
            "industry_codes": ["C13", "D44"],
        }
    },
    scenario={"scenario_id": "demo-park", "baseline_year": 2023},
    inputs={
        "csv_paths": ["data/sample_park.csv"],
        "pdf_paths": ["data/policy_brief.pdf"],
        "excel_paths": ["data/cashflow.xlsx"],
    },
)

print(state["envelopes"]["report"]["artifacts"]["report_path"])  # 输出 report.md 的路径
```

也可以直接运行内置 Demo：

```bash
python -m multi_energy_agent.runner
```

## 4. 输入与输出

- 输入（通过 `run_scenario(..., inputs=...)` 指定）：
  - `csv_paths: list[str]`
  - `pdf_paths: list[str]`
  - `excel_paths: list[str]`
- 输出（位于 `outputs/<scenario_id>/`）：
  - `plan.md`：任务清单 + 进度日志（每次关键步骤都会刷新），文件末尾嵌入机器可读 JSON 状态
  - `artifacts/`：`inventory.json`、CSV 画像、PDF 摘要、Excel 表格、`qa_index.json` 等
  - `report.md`：最终报告（保证中文字符数 ≥ 1000），自动汇总 DataGap 与证据引用
  - `state["review_items"]`：需要人工补齐/确认的检查点提示（例如缺少 admin_codes、未提供 PDF/Excel 等）

## 5. 配置项（环境变量）

- `OPENAI_API_KEY`：启用 LLM 增强；未设置则走 fallback 文本
- `OPENAI_MODEL`、`OPENAI_TEMPERATURE`：可选，控制 LLM 行为（默认 `gpt-4o-mini` / `0.2`）
- `POLICY_KG_PATH`：指定政策知识图谱 JSON 路径；未设置时使用 `data/mock_policy_kg.json`

## 6. 工作原理（简述）

- DataIntakeAgent
  - 扫描 CSV/PDF/Excel，生成 `inventory.json`、基础画像与占位说明；初始化并持续刷新 `plan.md`
- InsightSynthesisAgent
  - 基于选择元数据 + Intake 产物，给出基线描述、措施筛选、政策条款匹配与补贴聚合、财务/能流叙事（尽量使用已有数据，不做重型优化）
- ReportOrchestratorAgent
  - 汇总产物，生成规范化的 Markdown 报告（中文字符 ≥ 1000），保存 `report.md`，并产出 `qa_index.json`

## 7. 常见问题

- 中文乱码/问号：请使用 UTF-8 编码查看与保存文件；本项目所有文本文件均以 UTF-8 编写
- 缺少第三方库：对应能力会降级并记录 DataGap，建议按需安装 `pandas`/`openpyxl`/`pypdf`
- 未设置 LLM Key：报告仍可生成，只是部分叙事采用 fallback 文本

## 8. 下一步与扩展

- 替换为真实政策 KG：将导出的 JSON 路径写入 `POLICY_KG_PATH`
- 对接 UI/API：直接使用 `run_scenario` 返回的 `state["envelopes"][stage]` 中的 `artifacts/metrics`
- 增强计算：如需能流计算或优化求解，建议在 Agent 之外先离线得到结果（CSV/Excel/JSON），再交由 Agent 做解释与报告

