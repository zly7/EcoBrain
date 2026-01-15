"""Measure screener agent."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import AgentRunResult, BaseAgent
from ..schemas import Assumption, DataGap, Stage


MEASURE_LIBRARY = [
    {
        "id": "PV_ROOF",
        "name": "屋顶光伏",
        "target_scope": "scope2",
        "base_score": 0.72,
        "reduction_ratio": 0.18,
        "required_inputs": ["roof_area_m2", "solar_profile"],
    },
    {
        "id": "WASTE_HEAT",
        "name": "余热回收+热泵",
        "target_scope": "scope1",
        "base_score": 0.65,
        "reduction_ratio": 0.12,
        "required_inputs": ["waste_heat_profile", "steam_grade"],
    },
    {
        "id": "BESS_TOU",
        "name": "储能削峰填谷",
        "target_scope": "scope2",
        "base_score": 0.58,
        "reduction_ratio": 0.07,
        "required_inputs": ["tou_tariff", "load_profile"],
    },
    {
        "id": "EE_MOTOR",
        "name": "高效电机与变频改造",
        "target_scope": "scope2",
        "base_score": 0.61,
        "reduction_ratio": 0.09,
        "required_inputs": ["motor_inventory", "operating_hours"],
    },
]


class MeasureScreenerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(stage=Stage.MEASURES, name="measure_screener")

    def run(self, state) -> AgentRunResult:  # type: ignore[override]
        baseline_metrics = self._get_envelope_metrics(state, Stage.BASELINE)
        selection_metadata = (state.get("selection") or {}).get("metadata") or {}
        scenario = state.get("scenario") or {}

        total_emissions = baseline_metrics.get("total_emissions_tco2") or 1000.0
        electricity_price = scenario.get("electricity_price", 0.72)
        carbon_price = scenario.get("carbon_price", 45.0)

        available_fields = set(selection_metadata.keys()) | set(scenario.keys())
        measures_payload: List[Dict[str, Any]] = []
        high_severity_gaps: List[DataGap] = []

        for measure in MEASURE_LIBRARY:
            missing_inputs = sorted(set(measure["required_inputs"]) - available_fields)
            missing_penalty = 0.1 * len(missing_inputs)
            score = max(0.35, measure["base_score"] - missing_penalty)
            if measure["target_scope"] == "scope2" and electricity_price > 0.7:
                score += 0.05
            if measure["target_scope"] == "scope1" and carbon_price > 60:
                score += 0.03
            score = min(0.95, score)

            reduction = round(total_emissions * measure["reduction_ratio"], 2)
            capex_million = round(reduction * 0.015, 2)
            annual_savings = round(reduction * (electricity_price * 0.1 + carbon_price * 0.02), 2)

            measures_payload.append(
                {
                    "id": measure["id"],
                    "name": measure["name"],
                    "target_scope": measure["target_scope"],
                    "applicability_score": round(score, 2),
                    "expected_reduction_tco2": reduction,
                    "capex_million_cny": capex_million,
                    "annual_net_savings_million_cny": annual_savings,
                    "missing_inputs": missing_inputs,
                }
            )

            if missing_inputs:
                high_severity_gaps.append(
                    DataGap(
                        missing=f"{measure['id']}:{','.join(missing_inputs)}",
                        impact=f"Cannot finalize {measure['name']} sizing",
                        severity="medium" if len(missing_inputs) < 2 else "high",
                    )
                )

        measures_payload.sort(key=lambda x: x["applicability_score"], reverse=True)
        top_measures = measures_payload[:4]
        confidence = min(0.9, 0.55 + 0.1 * len([m for m in top_measures if not m["missing_inputs"]]))

        data_gaps = high_severity_gaps
        artifacts = {
            "candidate_measures": top_measures,
            "required_data_for_top10": sorted(
                {
                    req
                    for measure in MEASURE_LIBRARY
                    for req in measure["required_inputs"]
                    if req not in available_fields
                }
            ),
        }

        assumptions = [
            Assumption(
                name="reduction_ratio_source",
                value="demand_side_library_v0.2",
                reason="Derived from mentor supplied measure templates",
            )
        ]
        evidence = [
            self._build_evidence(
                description="Baseline total emissions used for proportional reduction",
                source="baseline_envelope",
            )
        ]

        envelope = self._create_envelope(
            state=state,
            metrics={"top_measures": top_measures},
            artifacts=artifacts,
            assumptions=assumptions,
            evidence=evidence,
            confidence=confidence,
            data_gaps=data_gaps,
        )

        review_items = []
        if data_gaps:
            review_items.append(
                self._review_item(
                    checkpoint_id="measure_data_gap",
                    issue="Top measures missing critical sizing inputs",
                    editable_fields=["candidate_measures", "required_data_for_top10"],
                    suggested_action="Upload roof area, TOU tariff, and process heat curves.",
                    severity="high",
                )
            )
        return AgentRunResult(envelope=envelope, review_items=review_items)
