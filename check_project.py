#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目结构和配置检查脚本
"""

import os
import sys
from pathlib import Path


def check_file_exists(path: str, description: str) -> bool:
    """检查文件是否存在"""
    if Path(path).exists():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description} 缺失: {path}")
        return False


def check_directory_exists(path: str, description: str) -> bool:
    """检查目录是否存在"""
    if Path(path).is_dir():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description} 缺失: {path}")
        return False


def check_import(module_path: str, description: str) -> bool:
    """检查模块是否可以导入"""
    try:
        __import__(module_path)
        print(f"✅ {description}: {module_path}")
        return True
    except ImportError as e:
        print(f"❌ {description} 导入失败: {module_path}")
        print(f"   错误: {e}")
        return False


def check_env_var(var_name: str, description: str, required: bool = False) -> bool:
    """检查环境变量"""
    value = os.environ.get(var_name)
    if value:
        print(f"✅ {description}: {var_name}={value[:20]}...")
        return True
    else:
        if required:
            print(f"❌ {description} 未设置: {var_name}")
        else:
            print(f"⚠️  {description} 未设置（可选）: {var_name}")
        return not required


def main():
    """主检查函数"""
    print("=" * 70)
    print("  EcoBrain 项目结构和配置检查")
    print("=" * 70)
    print()
    
    all_ok = True
    
    # 1. 核心目录检查
    print("📁 核心目录检查:")
    print("-" * 70)
    all_ok &= check_directory_exists("multi_energy_agent", "核心代码目录")
    all_ok &= check_directory_exists("multi_energy_agent/agents", "Agent 目录")
    all_ok &= check_directory_exists("multi_energy_agent/api", "API 目录")
    all_ok &= check_directory_exists("multi_energy_agent/tools", "工具目录")
    all_ok &= check_directory_exists("multi_energy_agent/reporting", "报告生成目录")
    all_ok &= check_directory_exists("other_back_data", "后端数据目录")
    all_ok &= check_directory_exists("eco_knowledge_graph", "知识图谱目录")
    all_ok &= check_directory_exists("frontend", "前端目录")
    all_ok &= check_directory_exists("docs", "文档目录")
    print()
    
    # 2. 核心文件检查
    print("📄 核心文件检查:")
    print("-" * 70)
    all_ok &= check_file_exists("multi_energy_agent/__init__.py", "包初始化文件")
    all_ok &= check_file_exists("multi_energy_agent/runner.py", "主运行器")
    all_ok &= check_file_exists("multi_energy_agent/chat_agent.py", "对话 Agent")
    all_ok &= check_file_exists("multi_energy_agent/llm.py", "LLM 客户端")
    all_ok &= check_file_exists("multi_energy_agent/agents/data_intake.py", "DataIntake Agent")
    all_ok &= check_file_exists("multi_energy_agent/agents/insight.py", "Insight Agent")
    all_ok &= check_file_exists("multi_energy_agent/agents/report.py", "Report Agent")
    all_ok &= check_file_exists("multi_energy_agent/api/main.py", "API 主文件")
    all_ok &= check_file_exists("multi_energy_agent/api/qa.py", "QA 服务")
    print()
    
    # 3. 脚本文件检查
    print("🔧 脚本文件检查:")
    print("-" * 70)
    all_ok &= check_file_exists("run_with_deepseek.sh", "DeepSeek 运行脚本")
    all_ok &= check_file_exists("start_api.sh", "API 启动脚本")
    all_ok &= check_file_exists("chat_cli.py", "命令行对话脚本")
    all_ok &= check_file_exists("query_park.py", "园区查询脚本")
    check_file_exists("run_custom_park.sh", "自定义运行脚本（可选）")
    check_file_exists("test_qa_restored.py", "QA 测试脚本（可选）")
    print()
    
    # 4. 前端文件检查
    print("🌐 前端文件检查:")
    print("-" * 70)
    all_ok &= check_file_exists("frontend/chat_interface.html", "对话界面")
    check_file_exists("frontend/api_client_demo.html", "API 客户端演示（可选）")
    check_file_exists("frontend/qa_chat_demo.html", "QA 聊天演示（可选）")
    print()
    
    # 5. 文档检查
    print("📚 文档检查:")
    print("-" * 70)
    all_ok &= check_file_exists("README.md", "项目说明")
    all_ok &= check_file_exists("QUICKSTART.md", "快速开始")
    all_ok &= check_file_exists("docs/如何运行项目.md", "运行指南")
    all_ok &= check_file_exists("docs/对话式Agent使用指南.md", "对话 Agent 指南")
    check_file_exists("docs/项目完整运作流程.md", "完整流程说明")
    check_file_exists("docs/FastAPI服务使用指南.md", "API 使用指南")
    print()
    
    # 6. 模块导入检查
    print("📦 模块导入检查:")
    print("-" * 70)
    all_ok &= check_import("multi_energy_agent", "核心包")
    all_ok &= check_import("multi_energy_agent.runner", "运行器模块")
    all_ok &= check_import("multi_energy_agent.chat_agent", "对话 Agent 模块")
    all_ok &= check_import("multi_energy_agent.llm", "LLM 模块")
    all_ok &= check_import("multi_energy_agent.agents.data_intake", "DataIntake Agent")
    all_ok &= check_import("multi_energy_agent.agents.insight", "Insight Agent")
    all_ok &= check_import("multi_energy_agent.agents.report", "Report Agent")
    all_ok &= check_import("multi_energy_agent.api.main", "API 主模块")
    print()
    
    # 7. 环境变量检查
    print("🔐 环境变量检查:")
    print("-" * 70)
    check_env_var("DEEPSEEK_API_KEY", "DeepSeek API Key", required=False)
    check_env_var("OPENAI_BASE_URL", "OpenAI Base URL", required=False)
    check_env_var("OPENAI_MODEL", "OpenAI Model", required=False)
    print()
    
    # 8. 数据目录检查
    print("💾 数据目录检查:")
    print("-" * 70)
    all_ok &= check_directory_exists("other_back_data/fhd", "FHD 数据")
    all_ok &= check_directory_exists("other_back_data/lyx", "LYX 数据")
    all_ok &= check_directory_exists("other_back_data/fdf", "FDF 数据")
    all_ok &= check_directory_exists("eco_knowledge_graph/data", "政策文档数据")
    print()
    
    # 9. 输出目录检查
    print("📂 输出目录检查:")
    print("-" * 70)
    if Path("outputs").exists():
        scenarios = list(Path("outputs").iterdir())
        print(f"✅ 输出目录存在，包含 {len(scenarios)} 个场景")
        for scenario in scenarios[:5]:
            if scenario.is_dir():
                print(f"   - {scenario.name}")
        if len(scenarios) > 5:
            print(f"   ...（还有 {len(scenarios) - 5} 个场景）")
    else:
        print("⚠️  输出目录不存在（首次运行时会自动创建）")
    print()
    
    # 总结
    print("=" * 70)
    if all_ok:
        print("✅ 所有核心检查通过！项目配置正确。")
        print()
        print("🚀 快速开始:")
        print("   1. 命令行对话: python chat_cli.py")
        print("   2. Web 界面: ./start_api.sh && open frontend/chat_interface.html")
        print("   3. 生成报告: ./run_with_deepseek.sh")
    else:
        print("❌ 部分检查未通过，请修复上述问题。")
        print()
        print("💡 常见问题:")
        print("   1. 模块导入失败: pip install -r requirements.txt")
        print("   2. 文件缺失: 检查 git 仓库是否完整")
        print("   3. 环境变量: export DEEPSEEK_API_KEY=your-key")
    print("=" * 70)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
