"""Background execution utilities for FastAPI."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..agents import DataIntakeAgent, InsightSynthesisAgent, ReportOrchestratorAgent
from ..llm import StructuredLLMClient
from ..schemas import Stage
from .models import ScenarioStatus
from .store import ScenarioRun, ScenarioRunStore
from .websocket import WebSocketManager

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScenarioEventPublisher:
    """Records and pushes scenario events."""

    def __init__(self, store: ScenarioRunStore, ws_manager: WebSocketManager) -> None:
        self._store = store
        self._ws_manager = ws_manager

    def emit(
        self,
        run_id: str,
        event: str,
        *,
        stage: Optional[str] = None,
        message: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        envelope = {
            "event_id": uuid.uuid4().hex,
            "run_id": run_id,
            "event": event,
            "stage": stage,
            "message": message,
            "payload": payload or {},
            "created_at": utcnow(),
        }
        self._store.append_event(run_id, envelope)
        self._ws_manager.push(run_id, envelope)


class ScenarioExecutor:
    """Runs scenarios in the background and reports progress."""

    def __init__(self, store: ScenarioRunStore, publisher: ScenarioEventPublisher) -> None:
        self._store = store
        self._publisher = publisher

    async def run(self, run_id: str) -> None:
        run = self._store.get(run_id)
        self._store.update_status(run_id, ScenarioStatus.RUNNING)
        self._publisher.emit(run_id, "run_started", message="Scenario execution started")
        loop = asyncio.get_running_loop()
        try:
            state = await loop.run_in_executor(None, self._execute_pipeline, run)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Scenario %s failed: %s", run_id, exc)
            self._store.update_status(run_id, ScenarioStatus.FAILED)
            self._store.set_error(run_id, str(exc))
            self._publisher.emit(run_id, "run_failed", message="Scenario execution failed", payload={"error": str(exc)})
            return

        self._store.set_result(run_id, state)
        self._store.update_status(run_id, ScenarioStatus.COMPLETED)
        report_artifacts = state.get("envelopes", {}).get(Stage.REPORT.value, {}).get("artifacts", {})
        payload = {}
        if "report_path" in report_artifacts:
            payload["report_path"] = report_artifacts["report_path"]
        self._publisher.emit(run_id, "run_completed", message="Scenario execution finished", payload=payload)

    def _execute_pipeline(self, run: ScenarioRun) -> Dict[str, Any]:
        llm: Optional[StructuredLLMClient] = None
        try:
            llm = StructuredLLMClient()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("LLM client initialization failed, continuing without LLM: %s", exc)

        state: Dict[str, Any] = {
            "selection": run.selection or {},
            "scenario": run.scenario or {},
            "inputs": run.inputs or {},
            "envelopes": {},
            "review_items": [],
        }

        pipeline = [
            DataIntakeAgent(llm=llm, output_root=run.output_root),
            InsightSynthesisAgent(llm=llm),
            ReportOrchestratorAgent(llm=llm),
        ]

        for agent in pipeline:
            stage_value = agent.stage.value
            self._publisher.emit(
                run.run_id,
                "stage_started",
                stage=stage_value,
                message=f"{stage_value} stage started",
            )
            result = agent.run(state)
            state["envelopes"][stage_value] = result.envelope.as_dict()
            if result.review_items:
                state["review_items"].extend([ri.as_dict() for ri in result.review_items])
            metrics_count = len(result.envelope.metrics or {})
            review_count = len(result.review_items or [])
            payload = {
                "result_id": result.envelope.result_id,
                "metrics_count": metrics_count,
                "review_items": review_count,
            }
            self._publisher.emit(
                run.run_id,
                "stage_completed",
                stage=stage_value,
                message=f"{stage_value} stage completed",
                payload=payload,
            )

        return state


__all__ = ["ScenarioExecutor", "ScenarioEventPublisher"]
