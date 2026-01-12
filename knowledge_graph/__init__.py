"""Knowledge graph building utilities (mock + real pipelines).

This package is owned by DeFan and is intended to generate:
1) an enriched full park+policy knowledge graph (nodes/edges)
2) a policy subset JSON compatible with PolicyKnowledgeGraphAgent

Nothing in this package is required by the MVP pipeline unless you call it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_KG_MODULE_NAME = "knowledge_graph"
_AGENT_MODULE_NAME = "multi_enengy_agent"


@lru_cache()
def repo_root() -> Path:
    """Base repo directory shared by kg/agent modules."""
    return Path(__file__).resolve().parents[1]


@lru_cache()
def resolve_module_root(module_name: str) -> Path:
    """Return `<repo_root>/<module_name>`, raising if it does not exist."""
    candidate = repo_root() / module_name
    if not candidate.is_dir():
        raise FileNotFoundError(f"Expected module directory not found: {candidate}")
    return candidate


@lru_cache()
def resolve_package_root() -> Path:
    """Return the agent package root (`multi_enengy_agent`)."""
    return resolve_module_root(_AGENT_MODULE_NAME)


@lru_cache()
def resolve_data_dir() -> Path:
    """Return the default data directory under the agent package."""
    return resolve_package_root() / "data"


@lru_cache()
def resolve_mock_source_dir() -> Path:
    """Helper used by mock builders to keep paths consistent."""
    return resolve_data_dir() / "mock_sources"
