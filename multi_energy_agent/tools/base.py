from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field, ConfigDict, ValidationError


class ToolError(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = Field(..., description="Machine-readable error type")
    message: str = Field(..., description="Human readable error message")
    details: Optional[Dict[str, Any]] = None


class ToolResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    tool_call_id: str
    name: str
    ok: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[ToolError] = None
    elapsed_ms: int = 0


class BaseTool:
    """Base tool with schema validation, timeout, and safe error handling."""

    name: str = "base_tool"
    description: str = ""
    InputModel: Type[BaseModel] = BaseModel
    timeout_s: float = 20.0

    def invoke(self, params: Dict[str, Any], *, tool_call_id: Optional[str] = None) -> Dict[str, Any]:
        call_id = tool_call_id or uuid.uuid4().hex
        t0 = time.time()

        # validate input
        try:
            payload = self.InputModel(**(params or {}))
        except ValidationError as ve:
            resp = ToolResponse(
                tool_call_id=call_id,
                name=self.name,
                ok=False,
                data={},
                error=ToolError(type="validation_error", message=str(ve)),
                elapsed_ms=int((time.time() - t0) * 1000),
            )
            return resp.model_dump()

        # execute with timeout
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(self._run, payload)
                data = fut.result(timeout=self.timeout_s)
            resp = ToolResponse(
                tool_call_id=call_id,
                name=self.name,
                ok=True,
                data=data if isinstance(data, dict) else {"result": data},
                elapsed_ms=int((time.time() - t0) * 1000),
            )
            return resp.model_dump()
        except FuturesTimeout:
            resp = ToolResponse(
                tool_call_id=call_id,
                name=self.name,
                ok=False,
                data={},
                error=ToolError(type="timeout", message=f"Tool '{self.name}' timed out after {self.timeout_s}s"),
                elapsed_ms=int((time.time() - t0) * 1000),
            )
            return resp.model_dump()
        except Exception as e:  # never raise
            resp = ToolResponse(
                tool_call_id=call_id,
                name=self.name,
                ok=False,
                data={},
                error=ToolError(type="exception", message=str(e)),
                elapsed_ms=int((time.time() - t0) * 1000),
            )
            return resp.model_dump()

    def _run(self, payload: BaseModel) -> Dict[str, Any]:
        raise NotImplementedError
