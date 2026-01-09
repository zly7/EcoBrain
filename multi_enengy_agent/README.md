# multi_enengy_agent 使用说明

本目录包含一个围绕“园区低碳路线图”构建的多 Agent 流水线，实现 `geo → baseline → measures → policy → finance → report` 的确定性评估链路。各阶段统一遵循 ResultEnvelope/Blackboard 合同，可用于 LLM+规则混合协同、证据追溯与人工复核。

## 1. 目录速览

```
multi_enengy_agent/
├── agents/               # Geo/Baseline/Measures/Policy/Finance/Report 等 Agent
├── data/mock_policy_kg.json
│                         # 虚拟政策知识图谱（可替换成德帆导出的真实数据）
├── graph.py              # LangGraph wiring，按阶段顺序衔接节点
├── policy_kg.py          # KG 加载 + 匹配 + 补贴聚合工具
├── runner.py             # CLI 入口（默认顺序执行，可切换 LangGraph）
├── schemas.py            # ResultEnvelope、BlackboardState、Stage 等共享模型
└── README.md
```

## 2. 环境要求

- Python 3.10+
- 可选：安装 `langgraph` 与 OpenAI SDK；若未安装会自动降级为顺序执行/离线 LLM 回退。

## 3. 如何运行

```bash
# 推荐使用顺序模式跑通全链路
python -m multi_enengy_agent.runner --no-langgraph

# 若已安装 langgraph，可省略 --no-langgraph 直接跑图执行
python -m multi_enengy_agent.runner
```

运行完成后控制台会打印：

1. 已执行的阶段（包含新增的 `policy`）。
2. Review 队列里需要人工确认的 checkpoint 数。
3. Report 节选，附带“政策与激励匹配”章节，可在 UI 或 API 层直接复用。
4. 可选 `--dump-json` 把最终 BlackboardState 输出到 `<job_id>.json` 做审计或调试。

## 4. 虚拟政策知识图谱（mock_policy_kg.json）

- 该文件提供最小可用的政策/条款/激励结构，目的是先把 agent 逻辑跑通，后续只需替换为德帆产出的 JSON 或 API 返回。
- 默认路径：`multi_enengy_agent/data/mock_policy_kg.json`。如需加载真实 KG，可设置环境变量 `POLICY_KG_PATH=/path/to/your_kg.json`。
- 匹配规则：`admin_codes + industry_codes + measure_ids` 标签重叠即命中，多标签越具体得分越高。Agent 输出 `matched_clauses` 和 `incentives_by_measure`，Finance 会按测算 CAPEX 自动扣减补贴。

## 5. 流水线阶段概览

| 阶段      | 负责 Agent                    | 核心输出                                                                 |
|-----------|--------------------------------|--------------------------------------------------------------------------|
| geo       | `GeoResolverAgent`             | 标准化选区、面积、行政区划、数据完备度                                   |
| baseline  | `BaselineAgent`                | Scope1/2 能碳基线、强度指标、继承数据缺口                               |
| measures  | `MeasureScreenerAgent`        | 候选减排措施（含缺口提示），为政策匹配/财务准备 measure ids             |
| policy    | `PolicyKnowledgeGraphAgent`   | 匹配政策条款、生成 citation 列表、测算 CAPEX 补贴并写入 artifacts        |
| finance   | `FinanceIntegratorAgent`      | 同时输出补贴前后 CAPEX、年净收益、NPV、现金流表                         |
| report    | `ReportOrchestratorAgent`     | Markdown 报告（含政策章节）、汇总 data gaps、输出参数表                  |

所有阶段都在 envelope 的 `reproducibility` 字段写入 agent 版本、场景参数版本，policy 额外写入 `policy_kg_version`，方便跟踪 KG 数据源。

## 6. 自定义与扩展

1. **替换政策数据**：准备符合 plan1.md 中说明的 JSON 结构，将路径配置到 `POLICY_KG_PATH` 或覆盖默认文件。
2. **接入真实 LLM**：在运行时提供 `OPENAI_API_KEY`，Report 阶段即可调用 OpenAI；无 key 时自动使用 fallback。
3. **联调 UI/API**：流水线所有中间结果均存放在 BlackboardState 中，可在 `run_job` 返回值里按阶段读取 `envelopes['stage'].artifacts`。

如需进一步扩展（数据补齐 agent、能流计算、组合优化等），可以在 `graph.py` 中新增节点并沿袭同样的 ResultEnvelope 契约。欢迎继续按 GPT5PRO_plan/plan1.md 的路线推进。***
