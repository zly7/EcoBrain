"""Core schemas shared across agents.

Backend modeling policy:
- Use **Pydantic** models (per project requirement) for stable schema + validation.
- `BlackboardState` remains a simple dict for orchestration convenience.

Each stage emits a `ResultEnvelope` and the runner stores `envelope.as_dict()`
under `state["envelopes"][stage.value]`.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Stage(str, Enum):
    """Pipeline stages (agent count <= 4, recommended 3)."""

    INTAKE = "intake"   # Data intake & profiling (CSV/PDF/Excel) + back-data materialize
    INSIGHT = "insight" # Descriptive synthesis (no optimization)
    REPORT = "report"   # Final report (Markdown + PDF)


BlackboardState = Dict[str, Any]


def new_result_id(stage: Stage) -> str:
    return f"{stage.value}-{uuid.uuid4().hex[:12]}"


class Evidence(BaseModel):
    model_config = ConfigDict(extra="allow")

    evidence_id: str
    description: str
    source: str
    uri: Optional[str] = None
    page: Optional[int] = None
    excerpt: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class Assumption(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    value: Any
    unit: Optional[str] = None
    reason: str = ""
    source: Optional[str] = None
    sensitivity: str = "medium"  # low/medium/high

    def as_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class DataGap(BaseModel):
    model_config = ConfigDict(extra="allow")

    missing: str
    impact: str
    severity: str = "medium"  # low/medium/high

    def as_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class HumanReviewItem(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    checkpoint_id: str
    stage: Stage
    issue: str
    editable_fields: List[str]
    suggested_action: str
    severity: str = "medium"

    def as_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ResultEnvelope(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    result_id: str
    scenario_id: str
    region_id: str
    stage: Stage
    metrics: Dict[str, Any]
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    assumptions: List[Assumption] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    confidence: float = 0.5
    data_gaps: List[DataGap] = Field(default_factory=list)
    reproducibility: Dict[str, Any] = Field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        # keep field names stable for the frontend
        return self.model_dump()
