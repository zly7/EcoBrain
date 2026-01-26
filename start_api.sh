#!/bin/bash
# FastAPI服务启动脚本

echo "启动 multi_energy_agent FastAPI 服务..."
echo "=========================================="
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
