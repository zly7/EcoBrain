"""Core schemas shared across agents.

NOTE: This project uses a "blackboard" dict (`BlackboardState`) to pass structured
data between stages. Each stage emits a `ResultEnvelope`, and the runner stores
`envelope.as_dict()` under `state["envelopes"][stage.value]`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


class Stage(str, Enum):
    """Pipeline stages (agent count <= 4, recommended 3)."""

    INTAKE = "intake"   # Data intake & profiling (CSV/PDF/Excel)
    INSIGHT = "insight" # KG-driven description & deepresearch synthesis (no optimization)
    REPORT = "report"   # Final markdown report (>=1000 Chinese chars) + local save


BlackboardState = Dict[str, Any]


def new_result_id(stage: Stage) -> str:
    return f"{stage.value}-{uuid.uuid4().hex[:12]}"


@dataclass
class Evidence:
    evidence_id: str
    description: str
    source: str
    uri: Optional[str] = None
    page: Optional[int] = None
    excerpt: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Assumption:
    name: str
    value: Any
    unit: Optional[str] = None
    reason: str = ""
    source: Optional[str] = None
    sensitivity: str = "medium"

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DataGap:
    missing: str
    impact: str
    severity: str = "medium"  # low/medium/high

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HumanReviewItem:
    checkpoint_id: str
    stage: Stage
    issue: str
    editable_fields: List[str]
    suggested_action: str
    severity: str = "medium"

    def as_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["stage"] = self.stage.value
        return payload


@dataclass
class ResultEnvelope:
    result_id: str
    scenario_id: str
    region_id: str
    stage: Stage
    metrics: Dict[str, Any]
    artifacts: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[Assumption] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    confidence: float = 0.5
    data_gaps: List[DataGap] = field(default_factory=list)
    reproducibility: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "scenario_id": self.scenario_id,
            "region_id": self.region_id,
            "stage": self.stage.value,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
            "assumptions": [a.as_dict() for a in self.assumptions],
            "evidence": [e.as_dict() for e in self.evidence],
            "confidence": self.confidence,
            "data_gaps": [g.as_dict() for g in self.data_gaps],
            "reproducibility": self.reproducibility,
        }
