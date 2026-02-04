"""FastAPI application exposing scenario orchestration interfaces."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from ..schemas import Stage
from ..llm import StructuredLLMClient
from ..chat_agent import ChatAgent
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

# 初始化对话 Agent
chat_agent = ChatAgent(llm=llm_client)


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


@app.post("/api/v1/chat", tags=["chat"])
async def chat(message: str = Query(..., description="User message")) -> dict:
    """对话式查询 - 通过自然语言查询园区信息并生成报告"""
    try:
        response = chat_agent.chat(message)
        return {
            "message": message,
            "response": response,
            "conversation_history": chat_agent.get_history()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat/reset", tags=["chat"])
async def reset_chat() -> dict:
    """重置对话状态"""
    chat_agent.reset()
    return {"status": "ok", "message": "对话已重置"}


@app.get("/api/v1/scenarios/{scenario_id}/report/pdf", tags=["report"])
async def download_pdf_report(scenario_id: str) -> FileResponse:
    """下载 PDF 报告"""
    # 首先尝试从 multi_energy_agent/pdf 目录查找
    pdf_dir = Path(__file__).parent.parent / "pdf"

    # 查找匹配的 PDF 文件（可能带时间戳前缀）
    pdf_path = None
    if pdf_dir.exists():
        for f in pdf_dir.glob(f"*_{scenario_id}.pdf"):
            pdf_path = f
            break
        if not pdf_path:
            # 尝试不带时间戳的文件名
            simple_path = pdf_dir / f"{scenario_id}.pdf"
            if simple_path.exists():
                pdf_path = simple_path

    # 如果 pdf 目录没找到，尝试 outputs 目录
    if not pdf_path or not pdf_path.exists():
        pdf_path = Path("outputs") / scenario_id / "report.pdf"

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF 报告不存在: {scenario_id}")

    return FileResponse(
        path=str(pdf_path),
        filename=f"{scenario_id}_report.pdf",
        media_type="application/pdf"
    )


@app.get("/api/v1/scenarios/{scenario_id}/report/md", tags=["report"])
async def download_markdown_report(scenario_id: str) -> FileResponse:
    """下载 Markdown 报告"""
    md_path = Path("outputs") / scenario_id / "report.md"

    if not md_path.exists():
        raise HTTPException(status_code=404, detail=f"Markdown 报告不存在: {scenario_id}")

    return FileResponse(
        path=str(md_path),
        filename=f"{scenario_id}_report.md",
        media_type="text/markdown"
    )


@app.get("/api/v1/reports", tags=["report"])
async def list_reports() -> dict:
    """列出所有已生成的报告"""
    reports = []
    seen_scenarios = set()

    # 从 multi_energy_agent/pdf 目录获取 PDF
    pdf_dir = Path(__file__).parent.parent / "pdf"
    if pdf_dir.exists():
        for pdf_file in pdf_dir.glob("*.pdf"):
            # 解析文件名: YYYYMMDD_HHMMSS_scenario_id.pdf 或 scenario_id.pdf
            name = pdf_file.stem
            parts = name.split("_", 2)
            if len(parts) >= 3 and parts[0].isdigit():
                scenario_id = parts[2]
            else:
                scenario_id = name

            if scenario_id not in seen_scenarios:
                seen_scenarios.add(scenario_id)
                reports.append({
                    "scenario_id": scenario_id,
                    "has_pdf": True,
                    "has_md": False,
                    "pdf_size": pdf_file.stat().st_size,
                    "md_size": 0,
                    "pdf_path": str(pdf_file),
                })

    # 从 outputs 目录获取报告
    outputs_dir = Path("outputs")
    if outputs_dir.exists():
        for scenario_dir in outputs_dir.iterdir():
            if scenario_dir.is_dir():
                scenario_id = scenario_dir.name
                pdf_path = scenario_dir / "report.pdf"
                md_path = scenario_dir / "report.md"

                if pdf_path.exists() or md_path.exists():
                    if scenario_id in seen_scenarios:
                        # 更新已有记录
                        for r in reports:
                            if r["scenario_id"] == scenario_id:
                                r["has_md"] = md_path.exists()
                                r["md_size"] = md_path.stat().st_size if md_path.exists() else 0
                                break
                    else:
                        seen_scenarios.add(scenario_id)
                        reports.append({
                            "scenario_id": scenario_id,
                            "has_pdf": pdf_path.exists(),
                            "has_md": md_path.exists(),
                            "pdf_size": pdf_path.stat().st_size if pdf_path.exists() else 0,
                            "md_size": md_path.stat().st_size if md_path.exists() else 0,
                        })

    return {"reports": reports, "total": len(reports)}
