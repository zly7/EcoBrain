"""FastAPI application exposing scenario orchestration interfaces."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from fastapi import FastAPI, HTTPException, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware

from ..schemas import Stage
from ..llm import StructuredLLMClient
from .models import (
    ScenarioCreateResponse,
    ScenarioDetailResponse,
    ScenarioEvent,
    ScenarioRequest,
    ScenarioStatus,
    ScenarioSummary,
)
from .qa import ReportQAService
from .service import ScenarioEventPublisher, ScenarioExecutor
from .store import ScenarioRun, ScenarioRunStore
from .websocket import WebSocketManager

logger = logging.getLogger(__name__)

tags_metadata = [
    {"name": "scenarios", "description": "Create and inspect multi-energy scenario runs"},
    {"name": "qa", "description": "Interactive Q&A over generated reports"},
]

app = FastAPI(
    title="multi_energy_agent API",
    version="0.1.0",
    openapi_tags=tags_metadata,
)

# 添加CORS中间件支持前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = ScenarioRunStore()
ws_manager = WebSocketManager()
publisher = ScenarioEventPublisher(store, ws_manager)
executor = ScenarioExecutor(store, publisher)

# 初始化LLM客户端用于Q&A
llm_client = StructuredLLMClient()
qa_service = ReportQAService(llm_client=llm_client)


@app.on_event("startup")
async def on_startup() -> None:
    ws_manager.bind_loop(asyncio.get_running_loop())


def _background_error_handler(task: asyncio.Task) -> None:
    try:
        task.result()
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Background scenario task crashed: %s", exc)


def _schedule_run(run_id: str) -> None:
    task = asyncio.create_task(executor.run(run_id))
    task.add_done_callback(_background_error_handler)


def _to_summary(run: ScenarioRun) -> ScenarioSummary:
    return ScenarioSummary(
        run_id=run.run_id,
        scenario_id=run.scenario_id,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _to_detail(run: ScenarioRun) -> ScenarioDetailResponse:
    events: List[ScenarioEvent] = [ScenarioEvent(**item) for item in run.events]
    return ScenarioDetailResponse(
        run_id=run.run_id,
        scenario_id=run.scenario_id,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
        selection=run.selection,
        scenario=run.scenario,
        inputs=run.inputs,
        events=events,
        result=run.result,
        error=run.error,
    )


@app.get("/healthz", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "stages": ",".join(stage.value for stage in Stage)}


@app.post(
    "/api/v1/scenarios",
    status_code=201,
    response_model=ScenarioCreateResponse,
    tags=["scenarios"],
)
async def create_scenario(request: ScenarioRequest) -> ScenarioCreateResponse:
    run = store.create_run(request)
    _schedule_run(run.run_id)
    return ScenarioCreateResponse(
        run_id=run.run_id,
        scenario_id=run.scenario_id,
        status=run.status,
        created_at=run.created_at,
    )


@app.get("/api/v1/scenarios", response_model=List[ScenarioSummary], tags=["scenarios"])
async def list_scenarios() -> List[ScenarioSummary]:
    return [_to_summary(run) for run in store.list_runs()]


@app.get(
    "/api/v1/scenarios/{run_id}",
    response_model=ScenarioDetailResponse,
    tags=["scenarios"],
)
async def get_scenario(run_id: str) -> ScenarioDetailResponse:
    try:
        run = store.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_detail(run)


@app.websocket("/ws/scenarios/{run_id}")
async def scenario_progress(run_id: str, websocket: WebSocket) -> None:
    await ws_manager.connect(run_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:  # pylint: disable=broad-except
        pass
    finally:
        ws_manager.disconnect(run_id, websocket)


@app.post("/api/v1/scenarios/{scenario_id}/qa", tags=["qa"])
async def ask_question(scenario_id: str, question: str = Query(..., description="Question to ask")) -> dict:
    """Ask a question about a completed scenario report."""
    result = qa_service.answer_question(question, scenario_id)
    return result


@app.get("/api/v1/scenarios/{scenario_id}/qa/suggestions", tags=["qa"])
async def get_question_suggestions(scenario_id: str) -> dict:
    """Get suggested questions for a scenario."""
    suggestions = qa_service.get_suggested_questions(scenario_id)
    return {"scenario_id": scenario_id, "suggestions": suggestions}
