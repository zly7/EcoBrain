"""Simple sequential runner for the 3-agent pipeline.

This runner does NOT depend on LangGraph; it is intentionally minimal to keep
the project easy to integrate into other orchestration frameworks.

Usage (example):
    from multi_energy_agent.runner import run_scenario

    state = run_scenario(
        selection={"metadata": {"admin_code": "310000", "area_km2": 12.5}},
        scenario={"scenario_id": "park-001", "baseline_year": 2023},
        inputs={"csv_paths": ["data/park.csv"], "pdf_paths": ["a.pdf", "b.pdf"], "excel_paths": ["finance.xlsx"]},
    )
    print(state["envelopes"]["report"]["artifacts"]["report_path"])
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .agents import DataIntakeAgent, InsightSynthesisAgent, ReportOrchestratorAgent
from .llm import StructuredLLMClient
from .schemas import BlackboardState


def run_scenario(
    selection: Dict[str, Any],
    scenario: Dict[str, Any],
    inputs: Optional[Dict[str, Any]] = None,
    llm: Optional[StructuredLLMClient] = None,
    output_root: str = "outputs",
) -> BlackboardState:
    state: BlackboardState = {
        "selection": selection or {},
        "scenario": scenario or {},
        "inputs": inputs or {},
        "envelopes": {},
        "review_items": [],
    }

    pipeline = [
        DataIntakeAgent(llm=llm, output_root=output_root),
        InsightSynthesisAgent(llm=llm),
        ReportOrchestratorAgent(llm=llm),
    ]

    for agent in pipeline:
        result = agent.run(state)
        # store as dict (stable for downstream)
        state["envelopes"][agent.stage.value] = result.envelope.as_dict()
        if result.review_items:
            state["review_items"].extend([ri.as_dict() for ri in result.review_items])

    return state


if __name__ == "__main__":
    from pathlib import Path
    
    # Use generated mock data files
    data_dir = Path(__file__).parent / "data" / "mock_sources"
    
    demo_state = run_scenario(
        selection={
            "metadata": {
                "admin_code": "320500",  # 苏州市
                "area_km2": 15.3,
                "entity_count": 3,
                "industry_codes": ["C26", "C30", "C34"],
                # 补充措施所需的字段
                "roof_area_m2": 90000,  # 总屋顶面积
                "solar_profile": "available",  # 标记有光伏数据
                "waste_heat_profile": "available",  # 标记有余热数据
                "steam_grade": "medium_pressure",  # 蒸汽等级
                "load_profile": "available",  # 标记有负荷曲线
                "tou_tariff": "available",  # 标记有分时电价
                "motor_inventory": "available",  # 标记有电机清单
                "operating_hours": 7200,  # 平均运行小时数
            }
        },
        scenario={
            "scenario_id": "demo-park",
            "baseline_year": 2023,
            "electricity_price": 0.82,  # 平均电价
            "carbon_price": 50.0,  # 碳价
        },
        inputs={
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
                str(data_dir / "tou_tariff.csv"),
            ],
            "pdf_paths": [
                str(data_dir / "policy_brief.txt"),  # Using txt as PDF mock
            ],
            "excel_paths": [
                str(data_dir / "cashflow_analysis.csv"),  # Using CSV as Excel mock
            ],
        },
    )
    report_path = demo_state["envelopes"]["report"]["artifacts"]["report_path"]
    print(f"Report saved to: {report_path}")
