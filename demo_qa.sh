#!/bin/bash
# 问答功能快速演示脚本

echo "🚀 报告智能问答功能演示"
echo "======================================"
echo ""

# 检查API服务是否运行
echo "1. 检查API服务状态..."
if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
    echo "   ✓ API服务正在运行"
else
    echo "   ✗ API服务未运行"
    echo ""
    echo "请先启动API服务："
    echo "  ./start_api.sh"
    exit 1
fi

echo ""
echo "2. 打开问答界面..."
echo "   在浏览器中打开 qa_chat_demo.html"
echo ""

# 根据操作系统打开浏览器
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open qa_chat_demo.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open qa_chat_demo.html
else
    # Windows
    start qa_chat_demo.html
fi

echo "3. 或者使用命令行交互模式..."
echo ""
read -p "是否启动命令行交互模式？(y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    python test_qa.py --interactive
fi

echo ""
echo "======================================"
echo "✅ 演示完成！"
