# EcoBrain 快速开始

## 🚀 三步运行

### 1️⃣ 配置 API Key

```bash
export DEEPSEEK_API_KEY="sk-528ef67fe6c54700b6b9eb31fecff922"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-reasoner"
```

### 2️⃣ 运行查询

```bash
# 方式 A：使用默认配置（柳州市）
./run_with_deepseek.sh

# 方式 B：自定义查询
python query_park.py --city 上海 --industries 电子信息,新能源
```

### 3️⃣ 查看结果

```bash
# 查看报告
open outputs/demo-liuzhou/report.pdf

# 或查看其他场景
ls outputs/
```

---

## 📋 常用命令

### 查询不同园区

```bash
# 柳州汽车产业园
python query_park.py --city 柳州 --industries 汽车,机械

# 天津武清开发区
python query_park.py --province 天津 --city 天津 --district 武清

# 上海电子信息园
python query_park.py --city 上海 --industries 电子信息,新能源

# 深圳高新技术园
python query_park.py --city 深圳 --industries 高新技术,制造
```

### 查看帮助

```bash
python query_park.py --help
```

---

## 📊 输出文件

```
outputs/<scenario_id>/
├── report.md      # Markdown 报告
├── report.pdf     # PDF 报告（16 页）
├── plan.md        # 执行日志
└── artifacts/     # 中间数据
```

---

## ⏱️ 执行时间

- **总时间**：2-3 分钟
- **LLM 调用**：2 次
- **成本**：~$0.01/次

---

## 🔧 故障排查

### 问题：API Key 错误

```bash
# 重新设置
export DEEPSEEK_API_KEY="sk-528ef67fe6c54700b6b9eb31fecff922"
export OPENAI_BASE_URL="https://api.deepseek.com"
```

### 问题：PDF 生成失败

```bash
# 重新安装 WeasyPrint
pip install weasyprint

# macOS 安装依赖
brew install pango
```

### 问题：运行速度慢

- 正常：2-3 分钟
- 检查网络连接
- 检查 API 服务状态

---

## 📚 更多文档

- [完整运行指南](docs/如何运行项目.md)
- [项目架构说明](docs/项目完整运作流程.md)
- [代码结构说明](docs/项目结构说明.md)

---

## 💡 示例

### Python API 调用

```python
from multi_energy_agent.runner import run_scenario

state = run_scenario(
    selection={"metadata": {"city": "上海"}},
    scenario={"scenario_id": "shanghai-park"},
    inputs={}
)

print(state["envelopes"]["report"]["artifacts"]["report_path"])
```

### 批量查询

```bash
# 创建批处理脚本
cat > batch.sh << 'EOF'
python query_park.py --city 柳州 --industries 汽车
python query_park.py --city 上海 --industries 电子信息
python query_park.py --city 深圳 --industries 高新技术
EOF

chmod +x batch.sh
./batch.sh
```

---

**快速开始**：`./run_with_deepseek.sh` → 查看 `outputs/demo-liuzhou/report.pdf`
