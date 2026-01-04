"""GeoResolverAgent implementation."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import AgentRunResult, BaseAgent
from ..schemas import Assumption, DataGap, Stage


class GeoResolverAgent(BaseAgent):
    """Normalizes the input selection and estimates coverage quality."""

    def __init__(self) -> None:
        super().__init__(stage=Stage.GEO, name="geo_resolver")

    def run(self, state) -> AgentRunResult:  # type: ignore[override]
        selection = state.get("selection") or {}
        geometry = selection.get("geometry") or {}
        metadata = selection.get("metadata") or {}

        area = float(geometry.get("area_km2") or metadata.get("area_km2") or 12.5)
        admin_codes: List[str] = metadata.get("admin_codes") or []
        if not admin_codes and metadata.get("admin_code"):
            admin_codes = [metadata["admin_code"]]

        entity_count = int(max(5, round(area * 11.2)))

        data_layers = selection.get("available_layers") or []
        completeness = min(1.0, 0.35 + 0.1 * len(data_layers))
        if geometry:
            completeness += 0.2
        if admin_codes:
            completeness += 0.15
        completeness = min(1.0, completeness)

        metrics: Dict[str, Any] = {
            "area_km2": round(area, 3),
            "admin_codes": admin_codes,
            "entity_count_est": entity_count,
            "data_completeness_score": round(completeness, 2),
            "available_layers": data_layers,
        }

        assumptions = [
            Assumption(
                name="entity_density_per_km2",
                value=11.2,
                unit="entities/km2",
                reason="Estimated from historical industrial park averages",
                source="internal:geo_density_v1",
            )
        ]

        evidence_desc = "Administrative codes derived from selection metadata"
        evidence = [self._build_evidence(description=evidence_desc, source="admin_dataset:v2023.09")]

        data_gaps: List[DataGap] = []
        if not geometry:
            data_gaps.append(
                DataGap(
                    missing="polygon_geometry",
                    impact="Cannot compute precise area or cross-check land use mix",
                    severity="high",
                )
            )
        if completeness < 0.7:
            data_gaps.append(
                DataGap(
                    missing="high_resolution_layers",
                    impact="Need firm-level geocoding before baseline calibration",
                    severity="medium",
                )
            )

        artifacts = {"normalized_selection": selection}
        envelope = self._create_envelope(
            state=state,
            metrics=metrics,
            artifacts=artifacts,
            assumptions=assumptions,
            evidence=evidence,
            confidence=completeness,
            data_gaps=data_gaps,
        )

        review_items = []
        if completeness < 0.6:
            review_items.append(
                self._review_item(
                    checkpoint_id="geo_low_completeness",
                    issue="Data completeness score below 0.6",
                    editable_fields=["available_layers", "geometry"],
                    suggested_action="Confirm selection boundary and upload missing GIS layers.",
                    severity="high",
                )
            )
        return AgentRunResult(
            envelope=envelope,
            review_items=review_items,
            notes="Geo resolver completed",
        )
