"""In-memory store tracking scenario runs and their progress."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import ScenarioEvent, ScenarioRequest, ScenarioStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ScenarioRun:
    run_id: str
    scenario_id: str
    selection: Dict[str, Any]
    scenario: Dict[str, Any]
    inputs: Dict[str, Any]
    output_root: str
    status: ScenarioStatus = ScenarioStatus.PENDING
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    events: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ScenarioRunStore:
    """Thread-safe store for ScenarioRun records."""

    def __init__(self) -> None:
        self._runs: Dict[str, ScenarioRun] = {}
        self._lock = threading.Lock()

    def create_run(self, request: ScenarioRequest) -> ScenarioRun:
        run_id = uuid.uuid4().hex
        scenario_id = str(request.scenario.get("scenario_id"))
        run = ScenarioRun(
            run_id=run_id,
            scenario_id=scenario_id,
            selection=request.selection,
            scenario=request.scenario,
            inputs=request.inputs,
            output_root=request.output_root,
        )
        with self._lock:
            self._runs[run_id] = run
        return run

    def get(self, run_id: str) -> ScenarioRun:
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise KeyError(f"Run {run_id} not found") from exc

    def list_runs(self) -> List[ScenarioRun]:
        with self._lock:
            return list(self._runs.values())

    def update_status(self, run_id: str, status: ScenarioStatus) -> ScenarioRun:
        run = self.get(run_id)
        with self._lock:
            run.status = status
            run.updated_at = utcnow()
            return run

    def append_event(self, run_id: str, event: Dict[str, Any]) -> ScenarioEvent:
        run = self.get(run_id)
        with self._lock:
            run.events.append(event)
            run.updated_at = utcnow()
        return ScenarioEvent(**event)

    def set_result(self, run_id: str, result: Dict[str, Any]) -> None:
        run = self.get(run_id)
        with self._lock:
            run.result = result
            run.updated_at = utcnow()

    def set_error(self, run_id: str, error: str) -> None:
        run = self.get(run_id)
        with self._lock:
            run.error = error
            run.updated_at = utcnow()


__all__ = ["ScenarioRun", "ScenarioRunStore"]
