#!/bin/bash
# 自定义园区查询脚本
# 用法: ./run_custom_park.sh <scenario_id> <province> <city> <district> <park_name> [industry1,industry2,...]

# 设置 DeepSeek API
export DEEPSEEK_API_KEY="sk-528ef67fe6c54700b6b9eb31fecff922"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-reasoner"
export OPENAI_TEMPERATURE="1.0"
export OPENAI_MAX_TOKENS="8000"

# WeasyPrint 需要的库路径（macOS）
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"

# 获取参数
SCENARIO_ID=${1:-"custom-park"}
PROVINCE=${2:-""}
CITY=${3:-""}
DISTRICT=${4:-""}
PARK_NAME=${5:-""}
INDUSTRIES=${6:-""}

echo "=========================================="
echo "EcoBrain - 自定义园区查询"
echo "=========================================="
echo "场景 ID: $SCENARIO_ID"
echo "省份: $PROVINCE"
echo "城市: $CITY"
echo "区县: $DISTRICT"
echo "园区名称: $PARK_NAME"
echo "产业关键词: $INDUSTRIES"
echo "=========================================="
echo ""

# 创建临时 Python 脚本
cat > /tmp/run_custom_park.py << 'PYTHON_SCRIPT'
import sys
from multi_energy_agent.runner import run_scenario

# 从环境变量或命令行参数获取配置
scenario_id = sys.argv[1] if len(sys.argv) > 1 else "custom-park"
province = sys.argv[2] if len(sys.argv) > 2 else ""
city = sys.argv[3] if len(sys.argv) > 3 else ""
district = sys.argv[4] if len(sys.argv) > 4 else ""
park_name = sys.argv[5] if len(sys.argv) > 5 else ""
industries_str = sys.argv[6] if len(sys.argv) > 6 else ""

# 解析产业关键词
industries = [i.strip() for i in industries_str.split(",") if i.strip()] if industries_str else []

# 构建 metadata
metadata = {}
if province:
    metadata["province"] = province
if city:
    metadata["city"] = city
if district:
    metadata["district"] = district
if park_name:
    metadata["park_name"] = park_name
if industries:
    metadata["industry_keywords"] = industries

print(f"\n运行配置:")
print(f"  scenario_id: {scenario_id}")
print(f"  metadata: {metadata}")
print()

# 运行场景
state = run_scenario(
    selection={"metadata": metadata},
    scenario={
        "scenario_id": scenario_id,
        "baseline_year": 2023,
        "description": f"{city or province or ''}园区低碳规划"
    },
    inputs={}
)

# 输出结果
report_path = state["envelopes"]["report"]["artifacts"]["report_path"]
report_pdf = state["envelopes"]["report"]["artifacts"]["report_pdf_path"]
print(f"\n✅ 报告生成完成！")
print(f"📄 Markdown: {report_path}")
print(f"📕 PDF: {report_pdf}")
PYTHON_SCRIPT

# 运行 Python 脚本
python /tmp/run_custom_park.py "$SCENARIO_ID" "$PROVINCE" "$CITY" "$DISTRICT" "$PARK_NAME" "$INDUSTRIES"

# 清理临时文件
rm /tmp/run_custom_park.py
