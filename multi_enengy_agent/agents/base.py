"""Base classes and helpers shared by all agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..schemas import (
    Assumption,
    DataGap,
    Evidence,
    HumanReviewItem,
    ResultEnvelope,
    Stage,
    BlackboardState,
    new_result_id,
)

if TYPE_CHECKING:
    from ..llm import StructuredLLMClient  # pragma: no cover


@dataclass
class AgentRunResult:
    envelope: ResultEnvelope
    review_items: List[HumanReviewItem] = field(default_factory=list)
    notes: Optional[str] = None


class BaseAgent(ABC):
    """Shared logic for emitting ResultEnvelope compliant outputs."""

    agent_version = "0.1.0"

    def __init__(self, stage: Stage, name: str, llm: Optional["StructuredLLMClient"] = None):
        self.stage = stage
        self.name = name
        self.llm = llm

    def __call__(self, state: BlackboardState) -> AgentRunResult:
        return self.run(state)

    @abstractmethod
    def run(self, state: BlackboardState) -> AgentRunResult:
        ...

    def _get_envelope_metrics(self, state: BlackboardState, stage: Stage) -> Dict[str, Any]:
        envelopes = state.get("envelopes") or {}
        stage_data: Dict[str, Any] = envelopes.get(stage.value) or {}
        return stage_data.get("metrics") or {}

    def _get_envelope_artifacts(
        self, state: BlackboardState, stage: Stage, default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        envelopes = state.get("envelopes") or {}
        stage_data: Dict[str, Any] = envelopes.get(stage.value) or {}
        return stage_data.get("artifacts") or default or {}

    def _scenario_id(self, state: BlackboardState) -> str:
        scenario = state.get("scenario") or {}
        return str(scenario.get("scenario_id") or "default-scenario")

    def _region_id(self, state: BlackboardState) -> str:
        selection = state.get("selection") or {}
        metadata = selection.get("metadata") or {}
        return str(metadata.get("region_id") or metadata.get("admin_code") or "unknown-region")

    def _create_envelope(
        self,
        state: BlackboardState,
        metrics: Dict[str, Any],
        artifacts: Optional[Dict[str, Any]] = None,
        assumptions: Optional[List[Assumption]] = None,
        evidence: Optional[List[Evidence]] = None,
        confidence: float = 0.5,
        data_gaps: Optional[List[DataGap]] = None,
    ) -> ResultEnvelope:
        scenario_id = self._scenario_id(state)
        region_id = self._region_id(state)
        reproducibility = {
            "agent": self.name,
            "agent_version": self.agent_version,
        }
        envelope = ResultEnvelope(
            result_id=new_result_id(self.stage),
            scenario_id=scenario_id,
            region_id=region_id,
            stage=self.stage,
            metrics=metrics,
            artifacts=artifacts or {},
            assumptions=assumptions or [],
            evidence=evidence or [],
            confidence=confidence,
            data_gaps=data_gaps or [],
            reproducibility=reproducibility,
        )
        return envelope

    def _build_evidence(self, description: str, source: str, uri: Optional[str] = None) -> Evidence:
        return Evidence(
            evidence_id=f"{self.stage.value}-src",
            description=description,
            source=source,
            uri=uri,
        )

    def _review_item(
        self,
        checkpoint_id: str,
        issue: str,
        editable_fields: List[str],
        suggested_action: str,
        severity: str = "medium",
    ) -> HumanReviewItem:
        return HumanReviewItem(
            checkpoint_id=checkpoint_id,
            stage=self.stage,
            issue=issue,
            editable_fields=editable_fields,
            suggested_action=suggested_action,
            severity=severity,
        )
