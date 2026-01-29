#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试对话 Agent 的意图识别
"""

import os
os.environ.setdefault("DEEPSEEK_API_KEY", "sk-528ef67fe6c54700b6b9eb31fecff922")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.deepseek.com")
os.environ.setdefault("OPENAI_MODEL", "deepseek-reasoner")

from multi_energy_agent.chat_agent import ChatAgent


def test_intent_recognition():
    """测试意图识别"""
    agent = ChatAgent()
    
    test_cases = [
        # 查询园区
        ("广西省有多少个产业园区", "query_park"),
        ("查询柳州市汽车产业园区", "query_park"),
        ("天津武清开发区怎么样", "query_park"),
        ("上海有哪些电子信息产业园", "query_park"),
        ("深圳的高新技术园区", "query_park"),
        
        # 生成报告
        ("生成报告", "generate_report"),
        ("帮我做一份规划", "generate_report"),
        ("分析一下柳州市的园区", "generate_report"),
        
        # 询问问题
        ("有哪些减排措施", "ask_question"),
        ("基线排放是多少", "ask_question"),
        ("需要补充哪些数据", "ask_question"),
        
        # 一般对话
        ("你好", "general_chat"),
        ("谢谢", "general_chat"),
        ("你能做什么", "general_chat"),
    ]
    
    print("=" * 70)
    print("  意图识别测试")
    print("=" * 70)
    print()
    
    correct = 0
    total = len(test_cases)
    
    for message, expected_type in test_cases:
        intent = agent._analyze_intent(message)
        actual_type = intent.get("type")
        
        is_correct = actual_type == expected_type
        correct += is_correct
        
        status = "✅" if is_correct else "❌"
        print(f"{status} 消息: {message}")
        print(f"   预期: {expected_type}")
        print(f"   实际: {actual_type}")
        
        if intent.get("province"):
            print(f"   省份: {intent.get('province')}")
        if intent.get("city"):
            print(f"   城市: {intent.get('city')}")
        if intent.get("industries"):
            print(f"   产业: {intent.get('industries')}")
        
        print()
    
    print("=" * 70)
    print(f"测试结果: {correct}/{total} 正确 ({correct/total*100:.1f}%)")
    print("=" * 70)
    
    return correct == total


def test_park_query():
    """测试园区查询功能"""
    agent = ChatAgent()
    
    print("\n" + "=" * 70)
    print("  园区查询功能测试")
    print("=" * 70)
    print()
    
    # 测试广西查询
    print("测试: 广西省有多少个产业园区")
    print("-" * 70)
    response = agent.chat("广西省有多少个产业园区")
    print(response)
    print()
    
    return True


if __name__ == "__main__":
    print("开始测试...\n")
    
    # 测试意图识别
    intent_ok = test_intent_recognition()
    
    # 测试园区查询
    query_ok = test_park_query()
    
    if intent_ok and query_ok:
        print("\n✅ 所有测试通过！")
    else:
        print("\n❌ 部分测试失败")
