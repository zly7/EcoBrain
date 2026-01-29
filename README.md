# EcoBrain - 多能源园区低碳规划智能体系统

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> 基于 3 个 Agent 流水线的智能规划系统，最小化 LLM 依赖，优先使用确定性算法，所有结论可审计追溯。

## 🎯 核心特点

- **最小化 LLM 依赖**：仅在 2 处使用 LLM（CSV 深度分析 + 专业报告生成）
- **可审计性**：所有结论都能追溯到输入数据和算法
- **模块化设计**：3 个独立 Agent + 工具注册表 + 知识图谱
- **多种使用方式**：命令行、Python API、FastAPI Web 服务
- **内置数据源**：104,127 个园区数据 + 21 个政策文档

## 📊 系统架构

```
输入数据 → DataIntakeAgent → InsightSynthesisAgent → ReportOrchestratorAgent → 输出报告
           (LLM 深度分析)    (确定性算法)           (LLM 专业报告)
```

### 三阶段流水线

1. **DataIntakeAgent**（数据接入）
   - 扫描输入文件，生成数据清单
   - 调用 LLM 生成 CSV 深度分析（唯一的 LLM 调用）
   - 初始化任务计划

2. **InsightSynthesisAgent**（洞察综合）
   - FHD：匹配 104,127 个园区，生成园区画像
   - LYX：基于行业评分推断能源需求倾向
   - FDF：从 21 个政策文档中检索相关条款
   - 生成措施优先级列表（纯确定性算法）

3. **ReportOrchestratorAgent**（报告编排）
   - 调用 LLM 生成专业报告（第二次 LLM 调用）
   - 使用 WeasyPrint 生成 PDF
   - 保存所有中间产物

## 🚀 快速开始

### 方式 1：命令行运行（最简单）

```bash
# 使用 DeepSeek API
./run_with_deepseek.sh

# 查看结果
cat outputs/demo-liuzhou/report.md
open outputs/demo-liuzhou/report.pdf
```

**生成文件**：
- `outputs/demo-liuzhou/report.md`：Markdown 报告（~24KB）
- `outputs/demo-liuzhou/report.pdf`：PDF 报告（~359KB，16 页）
- `outputs/demo-liuzhou/plan.md`：任务执行日志
- `outputs/demo-liuzhou/artifacts/`：所有中间产物

### 方式 2：Python API

```python
from multi_energy_agent.runner import run_scenario

state = run_scenario(
    selection={
        "metadata": {
            "city": "柳州",
            "industry_keywords": ["汽车", "机械"]
        }
    },
    scenario={
        "scenario_id": "my-park",
        "baseline_year": 2023
    },
    inputs={}
)

# 获取报告路径
report_path = state["envelopes"]["report"]["artifacts"]["report_path"]
print(f"报告已生成: {report_path}")
```

### 方式 3：FastAPI Web 服务

```bash
# 启动服务
./start_api.sh

# 访问 Swagger 文档
open http://localhost:8000/docs

# 健康检查
curl http://localhost:8000/healthz
```

**API 端点**：
- `POST /api/v1/scenarios`：创建并运行场景
- `GET /api/v1/scenarios`：列出所有场景
- `GET /api/v1/scenarios/{run_id}`：查看场景详情
- `WebSocket /ws/scenarios/{run_id}`：实时进度推送

## 📦 安装依赖

```bash
# 基础依赖
pip install -r requirements.txt

# 配置 DeepSeek API（可选，用于 LLM 功能）
export DEEPSEEK_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-reasoner"
```

## 📁 项目结构

```
EcoBrain/
├── multi_energy_agent/      # 核心代码
│   ├── agents/              # 三个 Agent 实现
│   ├── api/                 # FastAPI Web 服务
│   ├── tools/               # 工具注册表
│   └── runner.py            # 主入口
├── other_back_data/         # 内置数据源
│   ├── fhd/                 # 104,127 个园区数据
│   ├── lyx/                 # 能源评分数据
│   └── fdf/                 # 政策知识图谱接口
├── eco_knowledge_graph/     # 21 个政策文档
├── outputs/                 # 输出结果（自动生成）
├── docs/                    # 项目文档
├── frontend/                # 前端界面
├── relative_tests/          # 测试脚本
├── run_with_deepseek.sh     # 运行脚本
└── start_api.sh             # API 启动脚本
```

详细说明见 [docs/项目结构说明.md](docs/项目结构说明.md)

## 📊 性能指标

| 指标 | 数值 |
|------|------|
| 总执行时间 | ~130 秒 |
| LLM 调用次数 | 2 次（DataIntake + Report） |
| LLM 成本 | ~$0.005-0.010/次 |
| 报告字符数 | ~24,000 字符 |
| PDF 页数 | 16 页 |
| 园区匹配数 | 127 个（从 104,127 中筛选） |
| 政策检索命中 | 6 条（从 174 个文本块） |
| 措施建议数 | 7 条 |

## 📚 文档

| 文档 | 说明 |
|------|------|
| [项目完整运作流程](docs/项目完整运作流程.md) | **必读**：完整的系统说明 |
| [项目结构说明](docs/项目结构说明.md) | 详细的目录结构和开发指南 |
| [DataIntakeAgent 说明](docs/DataIntakeAgent作用说明.md) | DataIntake 详细说明 |
| [Prompt 优化效果对比](docs/Prompt优化效果对比.md) | Prompt 优化记录 |
| [LLM 使用说明](docs/LLM使用说明.md) | LLM 配置和使用 |
| [PDF 字体跨平台说明](docs/PDF字体跨平台说明.md) | PDF 生成和字体配置 |

## 🧪 测试

```bash
# API 测试
python relative_tests/test_api.py

# Web API 测试
./relative_tests/test_web_api.sh
```

## 🧹 项目维护

```bash
# 清理临时文件（Python 缓存、日志等）
./cleanup_project.sh
```

## ⚠️ 注意事项

1. **QA 功能暂时禁用**
   - 需要实现 `_generate_qa_index()` 方法才能恢复
   - 详见 [docs/QA功能移除说明.md](docs/QA功能移除说明.md)

2. **LLM 配置**
   - 如果不配置 DeepSeek API，系统会使用 fallback 模板
   - 报告质量会下降，但核心功能仍可用

3. **数据源**
   - 不要修改 `other_back_data/` 中的数据
   - 这些是内置数据源，修改可能导致系统异常

## 🔗 相关链接

- **DeepSeek API**: https://platform.deepseek.com/
- **WeasyPrint 文档**: https://doc.courtbouillon.org/weasyprint/
- **FastAPI 文档**: https://fastapi.tiangolo.com/

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**快速开始**：`./run_with_deepseek.sh` → 查看 `outputs/demo-liuzhou/report.pdf`
