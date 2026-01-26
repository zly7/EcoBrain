#!/usr/bin/env python3
"""测试FastAPI接口的示例脚本"""

import requests
import json
import time
from pathlib import Path

# API基础URL
BASE_URL = "http://localhost:8000"

def test_healthcheck():
    """测试健康检查接口"""
    print("=" * 60)
    print("1. 测试健康检查接口")
    print("=" * 60)
    response = requests.get(f"{BASE_URL}/healthz")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def create_scenario():
    """创建一个新的场景运行"""
    print("=" * 60)
    print("2. 创建新的场景运行")
    print("=" * 60)
    
    # 构建请求数据
    data_dir = Path("multi_energy_agent/data/mock_sources")
    
    payload = {
        "selection": {
            "metadata": {
                "admin_code": "320500",
                "area_km2": 15.3,
                "entity_count": 3,
                "industry_codes": ["C26", "C30", "C34"],
                "roof_area_m2": 90000,
                "solar_profile": "available",
                "waste_heat_profile": "available",
                "steam_grade": "medium_pressure",
                "load_profile": "available",
                "tou_tariff": "available",
                "motor_inventory": "available",
                "operating_hours": 7200
            }
        },
        "scenario": {
            "scenario_id": "api-test-park",
            "baseline_year": 2023,
            "electricity_price": 0.82,
            "carbon_price": 50.0
        },
        "inputs": {
            "csv_paths": [
                str(data_dir / "roof_inventory.csv"),
                str(data_dir / "enterprise_registry.csv"),
                str(data_dir / "enterprise_energy_monthly_2023.csv"),
                str(data_dir / "industry_energy_scale.csv"),
                str(data_dir / "cashflow_analysis.csv"),
                str(data_dir / "energy_flow_analysis.csv"),
                str(data_dir / "solar_profile.csv"),
                str(data_dir / "waste_heat_profile.csv"),
                str(data_dir / "load_profile.csv"),
                str(data_dir / "motor_inventory.csv"),
                str(data_dir / "tou_tariff.csv")
            ],
            "pdf_paths": [
                str(data_dir / "policy_brief.txt")
            ],
            "excel_paths": [
                str(data_dir / "cashflow_analysis.csv")
            ]
        },
        "output_root": "outputs"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/scenarios", json=payload)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    print()
    
    return result["run_id"]

def get_scenario_detail(run_id):
    """获取场景运行详情"""
    print("=" * 60)
    print(f"3. 获取场景运行详情 (run_id: {run_id})")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/v1/scenarios/{run_id}")
    print(f"状态码: {response.status_code}")
    result = response.json()
    
    # 只打印关键信息
    print(f"运行ID: {result['run_id']}")
    print(f"场景ID: {result['scenario_id']}")
    print(f"状态: {result['status']}")
    print(f"创建时间: {result['created_at']}")
    print(f"更新时间: {result['updated_at']}")
    print(f"事件数量: {len(result['events'])}")
    
    if result.get('events'):
        print("\n最近的事件:")
        for event in result['events'][-5:]:  # 只显示最后5个事件
            print(f"  - [{event['event']}] {event.get('message', '')} (stage: {event.get('stage', 'N/A')})")
    
    if result.get('result'):
        print("\n结果摘要:")
        envelopes = result['result'].get('envelopes', {})
        for stage, envelope in envelopes.items():
            print(f"  - {stage}: {len(envelope.get('metrics', {}))} 个指标")
    
    if result.get('error'):
        print(f"\n错误: {result['error']}")
    
    print()
    return result

def list_scenarios():
    """列出所有场景运行"""
    print("=" * 60)
    print("4. 列出所有场景运行")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/v1/scenarios")
    print(f"状态码: {response.status_code}")
    scenarios = response.json()
    
    print(f"总共 {len(scenarios)} 个场景运行:\n")
    for scenario in scenarios:
        print(f"  - {scenario['scenario_id']} ({scenario['run_id'][:8]}...)")
        print(f"    状态: {scenario['status']}")
        print(f"    创建时间: {scenario['created_at']}")
        print()

def monitor_scenario(run_id, max_wait=60):
    """监控场景运行直到完成"""
    print("=" * 60)
    print(f"5. 监控场景运行 (run_id: {run_id})")
    print("=" * 60)
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = requests.get(f"{BASE_URL}/api/v1/scenarios/{run_id}")
        result = response.json()
        status = result['status']
        
        print(f"当前状态: {status} (已等待 {int(time.time() - start_time)}秒)")
        
        if status in ['completed', 'failed']:
            print(f"\n场景运行已{status}!")
            if status == 'completed' and result.get('result'):
                report_path = result['result'].get('envelopes', {}).get('report', {}).get('artifacts', {}).get('report_path')
                if report_path:
                    print(f"报告路径: {report_path}")
            return result
        
        time.sleep(2)
    
    print("\n超时：场景运行未在规定时间内完成")
    return None

def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("FastAPI 接口测试")
    print("=" * 60 + "\n")
    
    try:
        # 1. 健康检查
        test_healthcheck()
        
        # 2. 创建场景
        run_id = create_scenario()
        
        # 3. 等待一下让后台开始处理
        time.sleep(2)
        
        # 4. 获取详情
        get_scenario_detail(run_id)
        
        # 5. 监控直到完成
        final_result = monitor_scenario(run_id, max_wait=120)
        
        # 6. 列出所有场景
        list_scenarios()
        
        # 7. 最终详情
        if final_result:
            print("\n" + "=" * 60)
            print("最终结果")
            print("=" * 60)
            get_scenario_detail(run_id)
        
        print("\n✅ 测试完成!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到API服务器")
        print("请确保FastAPI服务正在运行:")
        print("  uvicorn multi_energy_agent.api.main:app --reload")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
