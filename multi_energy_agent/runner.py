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

import re
from typing import Any, Dict, Optional

from .agents import DataIntakeAgent, InsightSynthesisAgent, ReportOrchestratorAgent
from .llm import StructuredLLMClient
from .schemas import BlackboardState
from .tools import default_tool_registry
from .utils.logging import init_run_context


def run_scenario(
    selection: Dict[str, Any],
    scenario: Dict[str, Any],
    inputs: Optional[Dict[str, Any]] = None,
    llm: Optional[StructuredLLMClient] = None,
    output_root: str = "outputs",
) -> BlackboardState:
    raw_id = str((scenario or {}).get("scenario_id") or "default-scenario")
    scenario_id = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw_id).strip("-") or "default-scenario"
    output_dir = f"{output_root}/{scenario_id}"

    # Per-run logging
    run_ctx = init_run_context(scenario_id=scenario_id, output_dir=output_dir)

    # Tool registry (centralized)
    tools = default_tool_registry()

    # LLM client (optional) + log all direct interactions
    llm_client = llm or StructuredLLMClient()
    llm_client.run_context = run_ctx

    state: BlackboardState = {
        "selection": selection or {},
        "scenario": scenario or {},
        "inputs": inputs or {},
        "output_dir": output_dir,
        "run_context": run_ctx,
        "tools": tools,
        "envelopes": {},
        "review_items": [],
    }

    pipeline = [
        DataIntakeAgent(llm=llm_client, output_root=output_root),
        InsightSynthesisAgent(llm=llm_client),
        ReportOrchestratorAgent(llm=llm_client),
    ]

    for agent in pipeline:
        result = agent.run(state)
        # store as dict (stable for downstream)
        state["envelopes"][agent.stage.value] = result.envelope.as_dict()
        if result.review_items:
            state["review_items"].extend([ri.as_dict() for ri in result.review_items])

    return state


if __name__ == "__main__":
    demo_state = run_scenario(
        selection={
            "metadata": {
                # For best demo effect, set city to 柳州 so that the included local policy PDF is relevant.
                "city": "柳州市",
                "area_km2": 12.5,
                "entity_count": 180,
                "industry_keywords": ["汽车", "有色金属", "机械"],
            }
        },
        scenario={
            "scenario_id": "demo-liuzhou",
            "baseline_year": 2023,
        },
        inputs={},
    )
    report_path = demo_state["envelopes"]["report"]["artifacts"]["report_path"]
    report_pdf = demo_state["envelopes"]["report"]["artifacts"]["report_pdf_path"]
    print(f"Report saved to: {report_path}")
    print(f"PDF saved to: {report_pdf}")
