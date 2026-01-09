"""Policy knowledge graph matcher agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from .base import AgentRunResult, BaseAgent
from ..policy_kg import PolicyKnowledgeGraph, compute_incentives_by_measure
from ..schemas import Assumption, DataGap, Stage


DEFAULT_KG_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_policy_kg.json"


class PolicyKnowledgeGraphAgent(BaseAgent):
    """Deterministic policy KG matcher that emits auditable incentives."""

    agent_version = "0.1.0"

    def __init__(self, kg_path: str | None = None) -> None:
        super().__init__(stage=Stage.POLICY, name="policy_kg_matcher")
        self.kg_path = Path(kg_path or os.getenv("POLICY_KG_PATH") or DEFAULT_KG_PATH)
        self._kg: PolicyKnowledgeGraph | None = None

    def _load_kg(self) -> PolicyKnowledgeGraph:
        if self._kg is None:
            self._kg = PolicyKnowledgeGraph.load_json(self.kg_path)
        return self._kg

    def run(self, state) -> AgentRunResult:  # type: ignore[override]
        geo_metrics = self._get_envelope_metrics(state, Stage.GEO)
        measures_metrics = self._get_envelope_metrics(state, Stage.MEASURES)

        selection_metadata = (state.get("selection") or {}).get("metadata") or {}
        admin_codes = geo_metrics.get("admin_codes") or selection_metadata.get("admin_codes") or []

        industry_codes = (
            selection_metadata.get("industry_codes")
            or selection_metadata.get("industry_list")
            or selection_metadata.get("industries")
            or []
        )
        if isinstance(industry_codes, str):
            industry_codes = [industry_codes]

        top_measures: List[Dict[str, Any]] = measures_metrics.get("top_measures") or []
        measure_ids = [str(item.get("id")) for item in top_measures if item.get("id")]

        data_gaps: List[DataGap] = []
        if not admin_codes:
            data_gaps.append(
                DataGap(
                    missing="admin_codes",
                    impact="Policy scope matching may be inaccurate without region identifiers.",
                    severity="high",
                )
            )
        if not measure_ids:
            data_gaps.append(
                DataGap(
                    missing="measure_ids",
                    impact="Policy matching requires candidate measures from previous stage.",
                    severity="high",
                )
            )
        if not industry_codes:
            data_gaps.append(
                DataGap(
                    missing="industry_codes",
                    impact="Industry specific clauses cannot be filtered; results may be over-inclusive.",
                    severity="medium",
                )
            )

        matched: List[Dict[str, Any]] = []
        incentives_by_measure: Dict[str, Any] = {}
        kg_version = "unknown"
        confidence = 0.35

        try:
            kg = self._load_kg()
            kg_version = kg.kg_version

            matched = kg.match(
                admin_codes=admin_codes,
                industry_codes=industry_codes,
                measure_ids=measure_ids,
                top_k=30,
            )
            incentives_by_measure = compute_incentives_by_measure(top_measures, matched)

            matched_docs = {clause.get("doc_id") for clause in matched if clause.get("doc_id")}
            matched_by_measure: Dict[str, int] = {}
            for clause in matched:
                for mid in clause.get("measure_ids") or []:
                    matched_by_measure[mid] = matched_by_measure.get(mid, 0) + 1

            total_subsidy = round(
                sum(float(item.get("capex_subsidy_million_cny") or 0.0) for item in incentives_by_measure.values()),
                4,
            )

            metrics: Dict[str, Any] = {
                "kg_version": kg_version,
                "matched_clause_count": len(matched),
                "matched_doc_count": len(matched_docs),
                "matched_by_measure": matched_by_measure,
                "policy_capex_subsidy_total_million_cny": total_subsidy,
            }
            artifacts = {
                "kg_path": str(self.kg_path),
                "matched_clauses": matched,
                "incentives_by_measure": incentives_by_measure,
            }
            assumptions = [
                Assumption(
                    name="policy_match_rule",
                    value="tag_overlap(admin_codes, industry_codes?, measure_ids) + deterministic scoring",
                    reason="MVP deterministic policy matcher; replace when DeFan KG is connected.",
                    sensitivity="medium",
                    source=f"policy_kg:{kg_version}",
                )
            ]
            evidence = [
                self._build_evidence(
                    description=f"Policy KG loaded from {self.kg_path} (kg_version={kg_version})",
                    source="policy_kg_file",
                    uri=str(self.kg_path),
                )
            ]

            confidence = 0.55
            if matched:
                confidence += 0.20
            if admin_codes:
                confidence += 0.10
            if industry_codes:
                confidence += 0.05
            confidence -= 0.05 * len([gap for gap in data_gaps if gap.severity == "high"])
            confidence = max(0.15, min(0.90, confidence))

            envelope = self._create_envelope(
                state=state,
                metrics=metrics,
                artifacts=artifacts,
                assumptions=assumptions,
                evidence=evidence,
                confidence=confidence,
                data_gaps=data_gaps,
                reproducibility_extra={"policy_kg_version": kg_version},
            )
        except FileNotFoundError:
            metrics = {
                "kg_version": kg_version,
                "matched_clause_count": 0,
                "matched_doc_count": 0,
                "matched_by_measure": {},
                "policy_capex_subsidy_total_million_cny": 0.0,
            }
            artifacts = {
                "kg_path": str(self.kg_path),
                "matched_clauses": [],
                "incentives_by_measure": {},
            }
            data_gaps.append(
                DataGap(
                    missing="policy_kg_file",
                    impact="Policy matching disabled; cannot compute incentives/citations.",
                    severity="high",
                )
            )
            envelope = self._create_envelope(
                state=state,
                metrics=metrics,
                artifacts=artifacts,
                assumptions=[
                    Assumption(
                        name="policy_kg_missing",
                        value=str(self.kg_path),
                        reason="KG file not found; using empty matches.",
                        sensitivity="high",
                    )
                ],
                evidence=[],
                confidence=0.15,
                data_gaps=data_gaps,
                reproducibility_extra={"policy_kg_version": kg_version},
            )

        review_items = []
        if confidence < 0.6 or any(gap.severity == "high" for gap in data_gaps):
            review_items.append(
                self._review_item(
                    checkpoint_id="policy_kg_review",
                    issue="Policy KG matching has low confidence or missing critical inputs.",
                    editable_fields=[
                        "selection.metadata.industry_codes",
                        "selection.metadata.admin_codes",
                        "scenario",
                    ],
                    suggested_action="Provide admin_codes/industry_codes or replace mock KG with real data.",
                    severity="medium" if matched else "high",
                )
            )

        return AgentRunResult(envelope=envelope, review_items=review_items)
