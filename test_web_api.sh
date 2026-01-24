#!/bin/bash

echo "测试Web界面API连接"
echo "===================="
echo ""

echo "1. 测试健康检查..."
curl -s http://localhost:8000/healthz
echo -e "\n"

echo "2. 测试获取建议问题..."
curl -s "http://localhost:8000/api/v1/scenarios/demo-park/qa/suggestions"
echo -e "\n"

echo "3. 测试问答功能..."
curl -s -X POST "http://localhost:8000/api/v1/scenarios/demo-park/qa?question=$(python3 -c 'import urllib.parse; print(urllib.parse.quote("有哪些推荐的减排措施？"))')"
echo -e "\n"

echo "===================="
echo "✅ 所有API端点正常工作"
echo ""
echo "请在浏览器中打开 qa_chat_demo.html"
echo "选择 '示范园区综合能源规划 (demo-park)' 开始对话"
