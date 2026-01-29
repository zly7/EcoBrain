#!/bin/bash
# 使用 DeepSeek API 运行 EcoBrain 项目

export DEEPSEEK_API_KEY="sk-528ef67fe6c54700b6b9eb31fecff922"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-reasoner"
export OPENAI_TEMPERATURE="1.0"
export OPENAI_MAX_TOKENS="8000"

# WeasyPrint 需要的库路径（macOS）
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"

echo "=========================================="
echo "EcoBrain - DeepSeek Reasoner + WeasyPrint"
echo "=========================================="
echo "模型: $OPENAI_MODEL (推理模型)"
echo "Base URL: $OPENAI_BASE_URL"
echo "Temperature: $OPENAI_TEMPERATURE"
echo "Max Tokens: $OPENAI_MAX_TOKENS"
echo "PDF 生成: WeasyPrint"
echo "=========================================="
echo ""

python -m multi_energy_agent.runner
