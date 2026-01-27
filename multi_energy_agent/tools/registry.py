from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseTool


@dataclass
class ToolCallRecord:
    tool_call_id: str
    name: str
    params: Dict[str, Any]
    response: Dict[str, Any]


class ToolRegistry:
    """Central registry for tools.

    Notes on tool_call alignment:
    - The agent/LLM initiates a call with `tool_call_id`.
    - The tool must return the same `tool_call_id` in its response.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self.history: List[ToolCallRecord] = []

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return sorted(self._tools.keys())

    def call(self, name: str, params: Dict[str, Any], *, tool_call_id: Optional[str] = None) -> Dict[str, Any]:
        tool = self.get(name)
        call_id = tool_call_id or uuid.uuid4().hex
        if tool is None:
            resp = {
                "tool_call_id": call_id,
                "name": name,
                "ok": False,
                "data": {},
                "error": {"type": "not_found", "message": f"Tool not registered: {name}"},
                "elapsed_ms": 0,
            }
            self.history.append(ToolCallRecord(call_id, name, params, resp))
            return resp

        resp = tool.invoke(params, tool_call_id=call_id)
        self.history.append(ToolCallRecord(call_id, name, params, resp))
        return resp
