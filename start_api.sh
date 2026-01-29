#!/bin/bash
# FastAPI服务启动脚本

# 配置 DeepSeek API
export DEEPSEEK_API_KEY="sk-528ef67fe6c54700b6b9eb31fecff922"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-chat"
export OPENAI_MAX_TOKENS="4000"

# WeasyPrint 需要的库路径（macOS）
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"

echo "启动 multi_energy_agent FastAPI 服务..."
echo "=========================================="
echo "LLM配置: DeepSeek API (deepseek-chat)"
echo "PDF生成: WeasyPrint"
echo ""
echo "服务地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "ReDoc文档: http://localhost:8000/redoc"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

# 启动uvicorn服务
uvicorn multi_energy_agent.api.main:app --reload --host 0.0.0.0 --port 8000
