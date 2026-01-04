"""LangGraph pipeline wiring for the multi-agent layer."""

from __future__ import annotations

from typing import Callable, List, Optional

try:  # pragma: no cover - optional dependency
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover
    StateGraph = None  # type: ignore
    END = "__END__"

from .agents import (
    BaselineAgent,
    FinanceIntegratorAgent,
    GeoResolverAgent,
    MeasureScreenerAgent,
    ReportOrchestratorAgent,
)
from .agents.base import BaseAgent
from .llm import StructuredLLMClient
from .schemas import (
    BlackboardState,
    StageLogEntry,
    append_logs,
    append_review_items,
    empty_state,
    with_envelope,
)


def _agent_sequence(llm: Optional[StructuredLLMClient]) -> List[BaseAgent]:
    return [
        GeoResolverAgent(),
        BaselineAgent(),
        MeasureScreenerAgent(),
        FinanceIntegratorAgent(),
        ReportOrchestratorAgent(llm=llm),
    ]


def _apply_agent(state: BlackboardState, agent: BaseAgent) -> BlackboardState:
    log_entry = StageLogEntry(stage=agent.stage, status="running", detail=f"{agent.name} started")
    try:
        result = agent(state)
        log_entry.complete("success", detail=f"{agent.name} completed")
        updated = with_envelope(state, result.envelope)
        updated = append_review_items(updated, result.review_items)
    except Exception as exc:  # pragma: no cover - surfaced to caller
        log_entry.complete("failed", detail=str(exc))
        updated = append_logs(state, log_entry)
        raise
    updated = append_logs(updated, log_entry)
    return updated


def build_langgraph(llm: Optional[StructuredLLMClient] = None):
    if StateGraph is None:
        raise RuntimeError("LangGraph is not installed. Install `langgraph` to build the graph.")

    agents = _agent_sequence(llm)
    graph = StateGraph(BlackboardState)

    def _wrap(agent: BaseAgent) -> Callable[[BlackboardState], BlackboardState]:
        def node(state: BlackboardState) -> BlackboardState:
            return _apply_agent(state, agent)

        return node

    node_names = ["geo", "baseline", "measures", "finance", "report"]
    for name, agent in zip(node_names, agents):
        graph.add_node(name, _wrap(agent))

    graph.set_entry_point("geo")
    graph.add_edge("geo", "baseline")
    graph.add_edge("baseline", "measures")
    graph.add_edge("measures", "finance")
    graph.add_edge("finance", "report")
    graph.add_edge("report", END)
    return graph.compile()


def run_job(
    job_id: str,
    selection,
    scenario,
    llm: Optional[StructuredLLMClient] = None,
    prefer_langgraph: bool = True,
) -> BlackboardState:
    """Runs the full pipeline either through LangGraph or sequential fallback."""

    state = empty_state(job_id=job_id, selection=selection, scenario=scenario)
    agents = _agent_sequence(llm)

    if prefer_langgraph and StateGraph is not None:
        graph = build_langgraph(llm)
        return graph.invoke(state)

    # Sequential fallback.
    for agent in agents:
        state = _apply_agent(state, agent)
    return state
