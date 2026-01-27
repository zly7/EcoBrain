"""Tooling layer.

All tool definitions live under this package.

Why tools?
- Stable input schema (Pydantic)
- Structured output (JSON dict)
- Timeout + safe fallback (no stack trace to user)
- tool_call_id alignment for future ChatMessage.tool_calls integration
"""

from .registry import ToolRegistry
from .back_data import LoadFHDBackDataTool, LoadLYXEnergyScoresTool, MaterializeEcoKGTool, QueryEcoKGTool
from .pdf_report import RenderPDFReportTool


def default_tool_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(LoadFHDBackDataTool())
    reg.register(LoadLYXEnergyScoresTool())
    reg.register(MaterializeEcoKGTool())
    reg.register(QueryEcoKGTool())
    reg.register(RenderPDFReportTool())
    return reg


__all__ = [
    "ToolRegistry",
    "default_tool_registry",
    "LoadFHDBackDataTool",
    "LoadLYXEnergyScoresTool",
    "MaterializeEcoKGTool",
    "QueryEcoKGTool",
    "RenderPDFReportTool",
]
