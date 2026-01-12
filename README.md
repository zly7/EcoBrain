# energy_llm

知识图谱与多智能体流水线的内部联调仓库。`knowledge_graph` 负责生成调试用的 mock 数据与集成 KG，`multi_enengy_agent` 读取输出的 `mock_policy_kg.json` 等文件完成政策+财务评估。

## 当前执行流程
`knowledge_graph` 与 `multi_enengy_agent` 默认位于同一个仓库根目录，无需配置任何环境变量，脚本会自动将输出写入 `multi_enengy_agent/data`。

1. **生成 mock 数据与知识图谱**  
   ```bash
   python -m knowledge_graph.build_mock_kg
   ```  
   - 会调用 `knowledge_graph.mock_sources` 写出 `data/mock_sources/*`。  
   - 紧接着构建园区+政策 KG，输出：  
     - `multi_enengy_agent/data/mock_policy_kg.json`（供 PolicyKnowledgeGraphAgent 使用）  
     - `multi_enengy_agent/data/mock_park_policy_graph.json`（完整节点/边快照）。  
   - 运行结束终端会打印每个文件的绝对路径，便于检查。
2. **执行多阶段 Agent 流水线**  
   ```bash
   python -m multi_enengy_agent.runner --no-langgraph
   ```  
   - 若已安装 LangGraph，可去掉 `--no-langgraph` 使用图执行模式。  
   - Runner 会自动读取上一步生成的 `mock_policy_kg.json`，依次完成 `geo → baseline → measures → policy → finance → report`，并在控制台输出阶段摘要及最终报告要点。
3. **结果校验 / 二次开发**  
   - 所有阶段的中间结果都会写入 `BlackboardState`，可通过 `--dump-json` 导出供审计。  
   - 若需要替换为真实数据，只需提供政策 KG JSON 并设置 `POLICY_KG_PATH`，或扩展 `knowledge_graph` 读取真实源再运行步骤 2。

整个流程目前是“mock 数据 → 集成 KG → Agent 流水线”的闭环，可随时复现并验证最近在 `knowledge_graph` 的改动是否正常落地到业务链路。
