# EcoBrain - 多能源园区低碳规划智能系统

基于多智能体的绿色园区低碳发展规划系统，支持对话式交互、自动生成专业报告和 PDF 导出。

## 功能特点

- **对话式交互**：通过自然语言查询园区信息、生成规划报告
- **智能报告生成**：按照国家绿色园区政策文件结构自动生成专业报告
- **PDF 导出**：支持彩色美观的 PDF 报告下载
- **数据支持**：内置 10 万+ 园区数据和 21 个政策文档

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 或 yarn

### 1. 安装后端依赖

```powershell
# 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install fastapi uvicorn pydantic reportlab pandas geopandas shapely openai
```

### 2. 配置 API Key

编辑 `start_backend.ps1`，设置你的 OpenAI 兼容 API Key：

```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
$env:OPENAI_BASE_URL = "https://your-api-provider.com/v1"
$env:OPENAI_MODEL = "your-model-name"
```

> 支持任何 OpenAI 兼容的 API 服务

### 3. 安装前端依赖

```powershell
cd frontend
npm install
cd ..
```

### 4. 启动服务

在 VSCode 终端中：

**启动后端**（终端 1）：
```powershell
.\start_backend.ps1
```

**启动前端**（终端 2，新建终端）：
```powershell
.\start_frontend.ps1
```

### 5. 访问系统

- **前端界面**: http://localhost:3000
- **API 文档**: http://localhost:8000/docs

## 使用指南

### 对话式查询

在前端界面中，你可以：

1. **查询园区信息**
   - "查询柳州市汽车产业园区"
   - "广西有多少个产业园区"
   - "天津武清开发区怎么样"

2. **生成规划报告**
   - "生成柳州市的低碳规划报告"
   - "帮我分析上海电子信息产业园"

3. **下载 PDF 报告**
   - 报告生成后，点击"下载 PDF"按钮

### API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/chat` | POST | 对话式查询 |
| `/api/v1/chat/reset` | POST | 重置对话 |
| `/api/v1/scenarios/{id}/report/pdf` | GET | 下载 PDF 报告 |
| `/api/v1/scenarios/{id}/report/md` | GET | 下载 Markdown 报告 |
| `/api/v1/reports` | GET | 列出所有报告 |

## 项目结构

```
energy_llm/
├── frontend/                # React 前端
│   ├── src/
│   │   ├── components/      # UI 组件
│   │   ├── hooks/           # React Hooks
│   │   └── lib/             # 工具函数
│   └── package.json
├── multi_energy_agent/      # 后端核心
│   ├── agents/              # 智能体实现
│   ├── api/                 # FastAPI 接口
│   ├── reporting/           # PDF 生成
│   └── tools/               # 工具函数
├── other_back_data/         # 数据源
│   ├── fhd/                 # 园区数据
│   ├── lyx/                 # 能源评分
│   └── fdf/                 # 政策接口
├── eco_knowledge_graph/     # 政策知识图谱
├── start_backend.ps1        # 后端启动脚本
└── start_frontend.ps1       # 前端启动脚本
```

## 常见问题

### Q: 报告生成失败怎么办？

1. 检查 DeepSeek API Key 是否正确配置
2. 确保网络连接正常
3. 查看后端日志排查错误

### Q: PDF 下载失败？

确保报告已经生成完成，可以在 `outputs/` 目录下查看是否有对应的 PDF 文件。

### Q: 前端无法连接后端？

1. 确保后端服务已启动（端口 8000）
2. 检查 CORS 配置
3. 确认前端代理配置正确

### Q: PowerShell 执行策略问题？

如果遇到脚本无法执行，运行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 技术栈

**后端**
- Python 3.10+
- FastAPI
- Pydantic
- ReportLab (PDF 生成)

**前端**
- React 18
- Vite 5
- TypeScript
- Tailwind CSS

## 许可证

MIT License
