"""CLI entry point for exercising the multi-agent pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .graph import run_job
from .llm import StructuredLLMClient


def _default_selection():
    return {
        "type": "polygon",
        "geometry": {"area_km2": 15.3},
        "metadata": {
            "region_id": "cn-suzhou-industrial-park",
            "admin_codes": ["320500", "320571"],
            "park_name": "示例产业园",
            "roof_area_m2": 180000,
            "waste_heat_profile": "available",
            "industry_codes": ["C26", "C30"],
        },
        "available_layers": ["admin_boundary", "firm_registry", "poi_energy"],
    }


def _default_scenario():
    return {
        "scenario_id": "demo-2025",
        "carbon_price": 60.0,
        "electricity_price": 0.82,
        "discount_rate": 0.08,
        "wacc": 0.09,
        "finance_horizon_years": 10,
        "param_version": "mvp-v1",
        "baseline_year": 2023,
        "grid_emission_factor_tco2_per_mwh": 0.57,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the MVP multi-agent pipeline.")
    parser.add_argument("--job-id", default="job-demo", help="Unique job identifier to embed inside envelopes.")
    parser.add_argument(
        "--no-langgraph", action="store_true", help="Force sequential fallback even if LangGraph is available."
    )
    parser.add_argument("--dump-json", action="store_true", help="Write final blackboard to job_id.json next to script.")
    args = parser.parse_args()

    selection = _default_selection()
    scenario = _default_scenario()
    llm = StructuredLLMClient()

    state = run_job(
        job_id=args.job_id,
        selection=selection,
        scenario=scenario,
        llm=llm,
        prefer_langgraph=not args.no_langgraph,
    )

    print("=== Pipeline completed ===")
    print(f"Job ID: {state.get('job_id')}")
    print(f"Stages: {', '.join(state.get('envelopes', {}).keys())}")
    print(f"Review checkpoints: {len(state.get('review_queue', []))}")
    report = (state.get("envelopes") or {}).get("report", {})
    report_md = (report.get("artifacts") or {}).get("report_markdown")
    if report_md:
        print("\n--- Report excerpt ---")
        print("\n".join(report_md.splitlines()[:20]))

    if args.dump_json:
        path = Path(f"{args.job_id}.json")
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        print(f"\nState dumped to {path.resolve()}")


if __name__ == "__main__":
    main()
