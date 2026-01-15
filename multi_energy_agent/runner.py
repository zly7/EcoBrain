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
    # Minimal demo run (no real files)
    demo_state = run_scenario(
        selection={"metadata": {"admin_code": "000000", "area_km2": 10, "entity_count": 12}},
        scenario={"scenario_id": "demo-park", "baseline_year": 2023},
        inputs={"csv_paths": [], "pdf_paths": [], "excel_paths": []},
    )
    report_path = demo_state["envelopes"]["report"]["artifacts"]["report_path"]
    print(f"Report saved to: {report_path}")
