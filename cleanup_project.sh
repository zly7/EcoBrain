#!/bin/bash
# 项目清理脚本 - 删除多余和临时文件

echo "🧹 开始清理项目..."

# 1. 删除 Python 缓存文件
echo "📦 清理 Python 缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

# 2. 删除 macOS 系统文件
echo "🍎 清理 macOS 系统文件..."
find . -name ".DS_Store" -delete 2>/dev/null

# 3. 删除测试文件和临时 PDF
echo "🧪 清理测试文件..."
rm -f test_*.py 2>/dev/null
rm -f test_*.pdf 2>/dev/null

# 4. 删除临时脚本
echo "📝 清理临时脚本..."
rm -f apply_prompt_optimization.py 2>/dev/null
rm -f install_weasyprint.sh 2>/dev/null

# 5. 删除日志文件
echo "📋 清理日志文件..."
rm -f api.log 2>/dev/null

# 6. 清理旧的输出目录（保留最新的）
echo "📂 清理旧的输出..."
# 保留 outputs/demo-liuzhou，删除其他
# (暂时不删除，让用户手动决定)

# 7. 删除废弃的 knowledge_graph 目录
echo "🗑️  删除废弃目录..."
rm -rf knowledge_graph 2>/dev/null

# 8. 整理文档到 docs 目录
echo "📚 整理文档..."
mkdir -p docs

# 移动所有 .md 文档到 docs 目录（除了 README.md）
for file in *.md; do
    if [ "$file" != "README.md" ]; then
        mv "$file" docs/ 2>/dev/null
    fi
done

echo "✅ 清理完成！"
echo ""
echo "📊 清理后的项目结构："
echo "  ├── docs/                    # 所有文档"
echo "  ├── eco_knowledge_graph/     # 政策知识图谱数据"
echo "  ├── frontend/                # 前端界面"
echo "  ├── multi_energy_agent/      # 核心代码"
echo "  ├── other_back_data/         # 后端数据源"
echo "  ├── outputs/                 # 输出结果"
echo "  ├── relative_tests/          # 测试脚本"
echo "  ├── logs_llm_direct/         # LLM 调用日志"
echo "  ├── logs_running/            # 运行日志"
echo "  ├── README.md                # 项目说明"
echo "  ├── run_with_deepseek.sh     # 运行脚本"
echo "  └── start_api.sh             # API 启动脚本"
