#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试恢复后的 QA 功能
"""

import os
import sys

# 设置 API Key
os.environ["DEEPSEEK_API_KEY"] = "sk-528ef67fe6c54700b6b9eb31fecff922"
os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com"
os.environ["OPENAI_MODEL"] = "deepseek-reasoner"

from multi_energy_agent.runner import run_scenario
from multi_energy_agent.api.qa import ReportQAService
from multi_energy_agent.llm import StructuredLLMClient

def test_qa_generation():
    """测试 QA 索引生成"""
    print("=" * 60)
    print("测试 QA 功能恢复")
    print("=" * 60)
    print()
    
    # 1. 运行一个小场景生成报告
    print("步骤 1: 生成报告...")
    state = run_scenario(
        selection={
            "metadata": {
                "city": "柳州",
                "industry_keywords": ["汽车", "机械"]
            }
        },
        scenario={
            "scenario_id": "qa-test",
            "baseline_year": 2023,
            "description": "QA 功能测试"
        },
        inputs={}
    )
    
    scenario_id = state["scenario"]["scenario_id"]
    print(f"✅ 报告生成完成: {scenario_id}")
    print()
    
    # 2. 检查 qa_index.json 是否生成
    print("步骤 2: 检查 qa_index.json...")
    import json
    from pathlib import Path
    
    qa_index_path = Path("outputs") / scenario_id / "artifacts" / "qa_index.json"
    if qa_index_path.exists():
        print(f"✅ qa_index.json 已生成: {qa_index_path}")
        
        # 读取并显示内容
        with open(qa_index_path, "r", encoding="utf-8") as f:
            qa_index = json.load(f)
        
        print()
        print("QA 索引内容:")
        print(f"  - 场景 ID: {qa_index.get('scenario_id')}")
        print(f"  - 基线排放: {qa_index.get('baseline', {}).get('total_emissions_tco2')} tCO2")
        print(f"  - 措施数量: {len(qa_index.get('measures', []))}")
        print(f"  - 政策数量: {len(qa_index.get('policies', []))}")
        print(f"  - 数据缺口: {len(qa_index.get('data_gaps', []))}")
        print()
        
        # 显示前 3 个措施
        print("推荐措施（前 3 项）:")
        for i, m in enumerate(qa_index.get("measures", [])[:3], 1):
            print(f"  {i}. {m.get('name')}")
            print(f"     - 评分: {m.get('applicability_score')}")
            print(f"     - 减排: {m.get('expected_reduction_tco2')} tCO2")
            print(f"     - 投资: {m.get('capex_million_cny')} 百万元")
            print(f"     - 回收期: {m.get('payback_years')} 年")
        print()
        
    else:
        print(f"❌ qa_index.json 未生成: {qa_index_path}")
        return False
    
    # 3. 测试 QA 服务
    print("步骤 3: 测试 QA 服务...")
    llm_client = StructuredLLMClient()
    qa_service = ReportQAService(llm_client=llm_client)
    
    # 测试问题列表
    test_questions = [
        "有哪些减排措施？",
        "园区的基线排放是多少？",
        "有哪些政策支持？",
        "需要补充哪些数据？",
    ]
    
    for question in test_questions:
        print(f"\n问题: {question}")
        print("-" * 60)
        
        result = qa_service.answer_question(question, scenario_id)
        
        print(f"回答: {result.get('answer')[:200]}...")
        print(f"置信度: {result.get('confidence')}")
        print(f"相关片段: {result.get('relevant_sections')}")
        print(f"来源数量: {len(result.get('sources', []))}")
    
    print()
    print("=" * 60)
    print("✅ QA 功能测试完成！")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_qa_generation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
