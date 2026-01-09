"""Finance integrator agent."""

from __future__ import annotations

from typing import Dict, List

from .base import AgentRunResult, BaseAgent
from ..schemas import Assumption, DataGap, Stage


class FinanceIntegratorAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(stage=Stage.FINANCE, name="finance_integrator")

    def run(self, state) -> AgentRunResult:  # type: ignore[override]
        measures_metrics = self._get_envelope_metrics(state, Stage.MEASURES)
        policy_artifacts = self._get_envelope_artifacts(state, Stage.POLICY, default={})
        scenario = state.get("scenario") or {}

        measures = measures_metrics.get("top_measures") or []
        incentives_by_measure = policy_artifacts.get("incentives_by_measure") or {}
        discount_rate = scenario.get("discount_rate", 0.08)
        wacc = scenario.get("wacc", 0.09)
        lifetime_years = scenario.get("finance_horizon_years", 10)

        gross_capex = 0.0
        total_incentive = 0.0
        total_capex = 0.0
        total_annual_net = 0.0
        cashflows: List[Dict[str, float]] = []
        for measure in measures:
            capex = float(measure.get("capex_million_cny") or 0.0)
            gross_capex += capex
            measure_id = str(measure.get("id") or "")
            incentive = float((incentives_by_measure.get(measure_id) or {}).get("capex_subsidy_million_cny") or 0.0)
            incentive = max(0.0, min(incentive, capex))
            total_incentive += incentive
            capex_net = capex - incentive
            annual_net = float(measure.get("annual_net_savings_million_cny") or 0.0)
            total_capex += capex_net
            total_annual_net += annual_net

        for year in range(1, lifetime_years + 1):
            discounted = total_annual_net / pow(1 + discount_rate, year)
            cashflows.append({"year": year, "discounted_net_million_cny": round(discounted, 4)})

        npv = round(sum(flow["discounted_net_million_cny"] for flow in cashflows) - total_capex, 2)
        payback = round(total_capex / total_annual_net, 2) if total_annual_net else None

        metrics = {
            "portfolio_capex_million_cny": round(total_capex, 2),
            "portfolio_capex_gross_million_cny": round(gross_capex, 2),
            "policy_incentive_million_cny": round(total_incentive, 2),
            "portfolio_annual_net_million_cny": round(total_annual_net, 2),
            "portfolio_npv_million_cny": npv,
            "portfolio_payback_years": payback,
            "discount_rate": discount_rate,
            "wacc": wacc,
            "finance_horizon_years": lifetime_years,
        }

        data_gaps: List[DataGap] = []
        if not measures:
            data_gaps.append(
                DataGap(
                    missing="measures",
                    impact="Finance module requires at least one candidate measure.",
                    severity="high",
                )
            )
        if total_annual_net <= 0:
            data_gaps.append(
                DataGap(
                    missing="annual_net_savings",
                    impact="Cannot compute NPV/payback without annual savings.",
                    severity="high",
                )
            )

        assumptions = [
            Assumption(
                name="finance_horizon_years",
                value=lifetime_years,
                unit="year",
                reason="Mentor guidance for MVP economic evaluation window",
            ),
            Assumption(
                name="discount_rate",
                value=discount_rate,
                unit="ratio",
                reason="Scenario level discount rate",
            ),
        ]
        evidence = [
            self._build_evidence(
                description="Measure capex and savings used for finance roll-up",
                source="measure_envelope",
            )
        ]

        artifacts = {"cashflow_table": cashflows}
        confidence = 0.55 if data_gaps else 0.72
        envelope = self._create_envelope(
            state=state,
            metrics=metrics,
            artifacts=artifacts,
            assumptions=assumptions,
            evidence=evidence,
            confidence=confidence,
            data_gaps=data_gaps,
        )

        review_items = []
        if payback and payback > lifetime_years:
            review_items.append(
                self._review_item(
                    checkpoint_id="finance_payback_warning",
                    issue="Portfolio payback exceeds finance horizon.",
                    editable_fields=["discount_rate", "candidate_measures"],
                    suggested_action="Revisit portfolio mix or update discount rate assumptions.",
                    severity="medium",
                )
            )
        if data_gaps:
            review_items.append(
                self._review_item(
                    checkpoint_id="finance_missing_inputs",
                    issue="Finance metrics missing essential inputs.",
                    editable_fields=["top_measures"],
                    suggested_action="Ensure each measure contains capex and savings estimates.",
                    severity="high",
                )
            )
        return AgentRunResult(envelope=envelope, review_items=review_items)
