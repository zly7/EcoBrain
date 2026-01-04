"""Baseline agent combines synthesizer + GHG accountant logic for MVP."""

from __future__ import annotations

from typing import Dict, List

from .base import AgentRunResult, BaseAgent
from ..schemas import Assumption, DataGap, Stage


class BaselineAgent(BaseAgent):
    """Produces Scope 1/2 baseline energy + emissions."""

    def __init__(self) -> None:
        super().__init__(stage=Stage.BASELINE, name="baseline_agent")

    def run(self, state) -> AgentRunResult:  # type: ignore[override]
        geo_metrics = self._get_envelope_metrics(state, Stage.GEO)
        scenario = state.get("scenario") or {}

        entity_count = geo_metrics.get("entity_count_est") or 12
        area = geo_metrics.get("area_km2") or 10.0
        completeness = geo_metrics.get("data_completeness_score") or 0.4

        # Simplified deterministic estimators.
        electricity_mwh = round(entity_count * 4.8 + area * 1.2, 2)
        thermal_mwh = round(entity_count * 3.1, 2)
        s1_emissions = round(thermal_mwh * 0.21, 2)
        grid_emission_factor = scenario.get("grid_emission_factor_tco2_per_mwh") or 0.58
        s2_emissions = round(electricity_mwh * grid_emission_factor, 2)
        combined = s1_emissions + s2_emissions

        metrics: Dict[str, float] = {
            "baseline_year": scenario.get("baseline_year", 2023),
            "electricity_mwh": electricity_mwh,
            "thermal_mwh": thermal_mwh,
            "scope1_emissions_tco2": s1_emissions,
            "scope2_emissions_tco2": s2_emissions,
            "total_emissions_tco2": combined,
            "energy_intensity_mwh_per_entity": round((electricity_mwh + thermal_mwh) / entity_count, 2),
            "data_quality_inherited": completeness,
        }

        assumptions: List[Assumption] = [
            Assumption(
                name="grid_emission_factor",
                value=grid_emission_factor,
                unit="tCO2/MWh",
                reason="Regional default from emission factor registry",
                source="factor_repo:v2023.07",
                sensitivity="high",
            ),
            Assumption(
                name="thermal_scope1_factor",
                value=0.21,
                unit="tCO2/MWh",
                reason="Average natural gas boiler emission factor",
                source="factor_repo:v2023.07",
                sensitivity="medium",
            ),
        ]

        evidence = [
            self._build_evidence(
                description="Geo normalized entity count used for baseline",
                source="geo_result_envelope",
            )
        ]

        data_gaps: List[DataGap] = []
        if completeness < 0.6:
            data_gaps.append(
                DataGap(
                    missing="metering_data",
                    impact="Baseline relies on regional intensity proxies",
                    severity="high",
                )
            )
        if entity_count < 8:
            data_gaps.append(
                DataGap(
                    missing="enterprise_roster",
                    impact="Need firm-level activity data before applying measures",
                    severity="medium",
                )
            )

        confidence = min(0.85, 0.5 + completeness / 2)
        envelope = self._create_envelope(
            state=state,
            metrics=metrics,
            assumptions=assumptions,
            evidence=evidence,
            confidence=confidence,
            data_gaps=data_gaps,
        )

        review_items = []
        if data_gaps:
            review_items.append(
                self._review_item(
                    checkpoint_id="baseline_proxy_warning",
                    issue="Baseline relies on proxy intensities. Confirm before continuing.",
                    editable_fields=["energy_intensity_mwh_per_entity", "assumptions"],
                    suggested_action="Replace with metered load profile if available.",
                    severity="high",
                )
            )
        return AgentRunResult(envelope=envelope, review_items=review_items)
