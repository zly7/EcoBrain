#!/usr/bin/env python3
"""测试报告问答功能"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_qa_functionality():
    """测试QA功能"""
    print("=" * 60)
    print("测试报告智能问答功能")
    print("=" * 60)
    print()
    
    # 1. 获取场景列表
    print("1. 获取已完成的场景...")
    response = requests.get(f"{API_BASE}/api/v1/scenarios")
    scenarios = response.json()
    
    completed_scenarios = [s for s in scenarios if s['status'] == 'completed']
    
    if not completed_scenarios:
        print("❌ 没有已完成的场景，请先运行场景")
        return
    
    scenario_id = completed_scenarios[0]['scenario_id']
    print(f"✓ 找到场景: {scenario_id}")
    print()
    
    # 2. 获取建议问题
    print("2. 获取建议问题...")
    response = requests.get(f"{API_BASE}/api/v1/scenarios/{scenario_id}/qa/suggestions")
    suggestions_data = response.json()
    suggestions = suggestions_data.get('suggestions', [])
    
    print(f"✓ 获取到 {len(suggestions)} 个建议问题:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"   {i}. {suggestion}")
    print()
    
    # 3. 测试问题
    test_questions = [
        "有哪些推荐的减排措施？",
        "园区的基线排放是多少？",
        "有哪些政策支持？",
        "还需要补充哪些数据？",
        "屋顶光伏的投资回报如何？"
    ]
    
    print("3. 测试问答功能...")
    print()
    
    for i, question in enumerate(test_questions, 1):
        print(f"问题 {i}: {question}")
        print("-" * 60)
        
        try:
            response = requests.post(
                f"{API_BASE}/api/v1/scenarios/{scenario_id}/qa",
                params={"question": question}
            )
            result = response.json()
            
            print(f"回答: {result['answer']}")
            print(f"置信度: {result['confidence']:.2f}")
            print(f"相关段落数: {result['relevant_sections']}")
            
            if result.get('sources'):
                print(f"信息来源:")
                for source in result['sources']:
                    if source['type'] == 'measure':
                        print(f"  - 措施: {source['name']}")
                    elif source['type'] == 'policy':
                        print(f"  - 政策: {source['citation']}")
                    elif source['type'] == 'data_gap':
                        print(f"  - 数据缺口: {source['missing']}")
            
            print()
        except Exception as e:
            print(f"❌ 错误: {e}")
            print()
    
    print("=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)

def interactive_qa():
    """交互式问答"""
    print("=" * 60)
    print("交互式问答模式")
    print("=" * 60)
    print()
    
    # 获取场景
    response = requests.get(f"{API_BASE}/api/v1/scenarios")
    scenarios = response.json()
    completed_scenarios = [s for s in scenarios if s['status'] == 'completed']
    
    if not completed_scenarios:
        print("❌ 没有已完成的场景")
        return
    
    print("可用场景:")
    for i, s in enumerate(completed_scenarios, 1):
        print(f"{i}. {s['scenario_id']} ({s['created_at']})")
    
    choice = input("\n选择场景 (输入序号): ").strip()
    try:
        scenario_id = completed_scenarios[int(choice) - 1]['scenario_id']
    except:
        print("无效选择")
        return
    
    print(f"\n已选择场景: {scenario_id}")
    print("输入 'quit' 退出\n")
    
    # 显示建议问题
    response = requests.get(f"{API_BASE}/api/v1/scenarios/{scenario_id}/qa/suggestions")
    suggestions = response.json().get('suggestions', [])
    if suggestions:
        print("💡 建议问题:")
        for i, s in enumerate(suggestions, 1):
            print(f"   {i}. {s}")
        print()
    
    # 交互循环
    while True:
        question = input("您的问题: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            break
        
        if not question:
            continue
        
        try:
            response = requests.post(
                f"{API_BASE}/api/v1/scenarios/{scenario_id}/qa",
                params={"question": question}
            )
            result = response.json()
            
            print(f"\n🤖 回答: {result['answer']}")
            print(f"   (置信度: {result['confidence']:.2f})\n")
            
        except Exception as e:
            print(f"❌ 错误: {e}\n")

if __name__ == "__main__":
    import sys
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
            interactive_qa()
        else:
            test_qa_functionality()
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到API服务器")
        print("请确保FastAPI服务正在运行:")
        print("  uvicorn multi_energy_agent.api.main:app --reload")
    except KeyboardInterrupt:
        print("\n\n👋 再见!")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
