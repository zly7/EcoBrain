"""Shared schemas used across the multi agent pipeline.

The classes in this module follow the guidance captured in 指引.md and
explicitly model the ResultEnvelope + shared blackboard contract so that
every agent can emit auditable, reproducible outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict
from uuid import uuid4
from datetime import datetime, timezone


class Stage(str, Enum):
    GEO = "geo"
    BASELINE = "baseline"
    MEASURES = "measures"
    FINANCE = "finance"
    REPORT = "report"


class Selection(TypedDict, total=False):
    type: str
    geometry: Dict[str, Any]
    metadata: Dict[str, Any]


class ScenarioContext(TypedDict, total=False):
    scenario_id: str
    carbon_price: float
    electricity_price: float
    wacc: float
    discount_rate: float
    param_version: str


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def new_result_id(stage: Stage) -> str:
    return f"{stage.value}-{uuid4().hex[:8]}"


@dataclass
class Assumption:
    name: str
    value: Any
    unit: Optional[str] = None
    reason: Optional[str] = None
    sensitivity: Optional[str] = None
    source: Optional[str] = None


@dataclass
class Evidence:
    evidence_id: str
    description: str
    source: str
    uri: Optional[str] = None
    retrieved_at: str = field(default_factory=_timestamp)


@dataclass
class DataGap:
    missing: str
    impact: str
    severity: str = "medium"


@dataclass
class HumanReviewItem:
    checkpoint_id: str
    stage: Stage
    issue: str
    editable_fields: List[str]
    suggested_action: str
    severity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["stage"] = self.stage.value
        return payload


@dataclass
class StageLogEntry:
    stage: Stage
    status: str
    detail: str
    started_at: str = field(default_factory=_timestamp)
    finished_at: Optional[str] = None

    def complete(self, status: str, detail: Optional[str] = None) -> None:
        self.status = status
        if detail:
            self.detail = detail
        self.finished_at = _timestamp()

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["stage"] = self.stage.value
        return payload


@dataclass
class ResultEnvelope:
    result_id: str
    scenario_id: str
    region_id: str
    stage: Stage
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[Assumption] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    confidence: float = 0.5
    data_gaps: List[DataGap] = field(default_factory=list)
    reproducibility: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "result_id": self.result_id,
            "scenario_id": self.scenario_id,
            "region_id": self.region_id,
            "stage": self.stage.value,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
            "assumptions": [asdict(a) for a in self.assumptions],
            "evidence": [asdict(e) for e in self.evidence],
            "confidence": self.confidence,
            "data_gaps": [asdict(g) for g in self.data_gaps],
            "reproducibility": self.reproducibility,
        }
        return payload


class BlackboardState(TypedDict, total=False):
    job_id: str
    selection: Selection
    scenario: ScenarioContext
    envelopes: Dict[str, Dict[str, Any]]
    review_queue: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]


def empty_state(job_id: str, selection: Selection, scenario: ScenarioContext) -> BlackboardState:
    return {
        "job_id": job_id,
        "selection": selection,
        "scenario": scenario,
        "envelopes": {},
        "review_queue": [],
        "logs": [],
    }


def with_envelope(state: BlackboardState, envelope: ResultEnvelope) -> BlackboardState:
    envelopes = dict(state.get("envelopes") or {})
    envelopes[envelope.stage.value] = envelope.to_dict()
    updated = dict(state)
    updated["envelopes"] = envelopes
    return updated


def append_review_items(
    state: BlackboardState, review_items: List[HumanReviewItem]
) -> BlackboardState:
    queue = list(state.get("review_queue") or [])
    queue.extend(item.to_dict() for item in review_items)
    updated = dict(state)
    updated["review_queue"] = queue
    return updated


def append_logs(state: BlackboardState, log_entry: StageLogEntry) -> BlackboardState:
    logs = list(state.get("logs") or [])
    logs.append(log_entry.to_dict())
    updated = dict(state)
    updated["logs"] = logs
    return updated
