#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EcoBrain 对话式命令行界面
"""

import os
import sys

# 设置 API Key
os.environ.setdefault("DEEPSEEK_API_KEY", "sk-528ef67fe6c54700b6b9eb31fecff922")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.deepseek.com")
os.environ.setdefault("OPENAI_MODEL", "deepseek-reasoner")

from multi_energy_agent.chat_agent import ChatAgent


def print_banner():
    """打印欢迎横幅"""
    print("=" * 70)
    print("  EcoBrain - 多能源园区低碳规划对话助手")
    print("=" * 70)
    print()
    print("我可以帮您：")
    print("  1. 查询全国 10 万+ 园区信息")
    print("  2. 生成专业的低碳规划报告")
    print("  3. 回答园区相关问题")
    print()
    print("示例：")
    print("  - 查询柳州市汽车产业园区")
    print("  - 生成天津武清开发区的报告")
    print("  - 有哪些减排措施？")
    print()
    print("输入 'exit' 或 'quit' 退出，输入 'reset' 重置对话")
    print("=" * 70)
    print()


def main():
    """主函数"""
    print_banner()
    
    # 初始化对话 Agent
    agent = ChatAgent()
    
    while True:
        try:
            # 获取用户输入
            user_input = input("\n👤 您: ").strip()
            
            if not user_input:
                continue
            
            # 处理特殊命令
            if user_input.lower() in ["exit", "quit", "退出"]:
                print("\n👋 再见！")
                break
            
            if user_input.lower() in ["reset", "重置"]:
                agent.reset()
                print("\n✅ 对话已重置")
                continue
            
            if user_input.lower() in ["help", "帮助"]:
                print_banner()
                continue
            
            # 处理用户消息
            print("\n🤖 助手: ", end="", flush=True)
            response = agent.chat(user_input)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            print("请重试或输入 'reset' 重置对话")


if __name__ == "__main__":
    main()
