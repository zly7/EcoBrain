"""Utilities for pushing scenario events to WebSocket clients."""

from __future__ import annotations

import asyncio
import threading
from collections import defaultdict
from typing import Any, Dict, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


class WebSocketManager:
    """Keeps track of open WebSocket connections per run_id."""

    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, run_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._connections[run_id].add(websocket)

    def disconnect(self, run_id: str, websocket: WebSocket) -> None:
        with self._lock:
            connections = self._connections.get(run_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(run_id, None)

    async def _broadcast(self, run_id: str, message: Dict[str, Any]) -> None:
        targets = []
        with self._lock:
            targets = list(self._connections.get(run_id, set()))
        to_remove: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except WebSocketDisconnect:
                to_remove.append(ws)
            except RuntimeError:
                to_remove.append(ws)
        if to_remove:
            with self._lock:
                for ws in to_remove:
                    self._connections.get(run_id, set()).discard(ws)

    def push(self, run_id: str, message: Dict[str, Any]) -> None:
        if not self._loop:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(run_id, message), self._loop)


__all__ = ["WebSocketManager"]
