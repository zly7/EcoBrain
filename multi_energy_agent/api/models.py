"""Pydantic models exposed by the FastAPI service."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ScenarioStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScenarioRequest(BaseModel):
    """Incoming payload describing a scenario run."""

    selection: Dict[str, Any] = Field(default_factory=dict)
    scenario: Dict[str, Any] = Field(default_factory=dict)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    output_root: str = Field(default="outputs", description="Filesystem root for artifacts")

    @model_validator(mode="after")
    def validate_scenario_id(self) -> "ScenarioRequest":
        scenario_id = (self.scenario or {}).get("scenario_id")
        if not scenario_id:
            raise ValueError("scenario.scenario_id is required to start a run")
        return self


class ScenarioEvent(BaseModel):
    event_id: str
    run_id: str
    event: str
    created_at: datetime
    stage: Optional[str] = None
    message: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class ScenarioCreateResponse(BaseModel):
    run_id: str
    scenario_id: str
    status: ScenarioStatus
    created_at: datetime


class ScenarioSummary(BaseModel):
    run_id: str
    scenario_id: str
    status: ScenarioStatus
    created_at: datetime
    updated_at: datetime


class ScenarioDetailResponse(ScenarioSummary):
    selection: Dict[str, Any]
    scenario: Dict[str, Any]
    inputs: Dict[str, Any]
    events: List[ScenarioEvent]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
