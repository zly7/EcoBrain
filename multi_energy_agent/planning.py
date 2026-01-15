"""PlanManager writes and refreshes `plan.md` (Claude-code style).

Key requirement:
- plan.md starts with ALL report tasks.
- After each significant step ("tool call" / agent step), refresh plan.md.
- The plan file remains human-readable Markdown but also contains an embedded
  machine-readable JSON state for reliable updates.

The embedded state is stored as a single-line HTML comment:

    <!-- PLAN_STATE: {...json...} -->

"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class PlanTask:
    task_id: str
    title: str
    status: str = "todo"  # todo/doing/done
    note: str = ""
    updated_at: str = field(default_factory=_utc_ts)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status,
            "note": self.note,
            "updated_at": self.updated_at,
        }


@dataclass
class PlanState:
    scenario_id: str
    created_at: str = field(default_factory=_utc_ts)
    last_updated: str = field(default_factory=_utc_ts)
    tasks: List[PlanTask] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "tasks": [t.as_dict() for t in self.tasks],
            "logs": list(self.logs),
        }


class PlanManager:
    def __init__(self, plan_path: Path) -> None:
        self.plan_path = plan_path
        self.state: Optional[PlanState] = None

    # ---------- public API ----------
    def init_plan(self, scenario_id: str, tasks: List[Dict[str, str]]) -> None:
        """Initialize a fresh plan file if it doesn't exist."""

        if self.plan_path.exists():
            self.state = self._load_state() or self._bootstrap_from_tasks(scenario_id, tasks)
            self.refresh("init_plan: plan existed, loaded state")
            return

        self.state = self._bootstrap_from_tasks(scenario_id, tasks)
        self.refresh("init_plan: created new plan")

    def mark_doing(self, task_id: str, note: str = "") -> None:
        self._ensure_loaded()
        task = self._find_task(task_id)
        if task:
            task.status = "doing"
            if note:
                task.note = note
            task.updated_at = _utc_ts()
            self.refresh(f"task {task_id} -> doing. {note}".strip())

    def mark_done(self, task_id: str, note: str = "") -> None:
        self._ensure_loaded()
        task = self._find_task(task_id)
        if task:
            task.status = "done"
            if note:
                task.note = note
            task.updated_at = _utc_ts()
            self.refresh(f"task {task_id} -> done. {note}".strip())

    def append_log(self, message: str) -> None:
        self._ensure_loaded()
        assert self.state is not None
        self.state.logs.append(f"{_utc_ts()} {message}")
        self.refresh("append_log")

    def refresh(self, reason: str = "") -> None:
        """Write the current plan state into plan.md (overwrite)."""
        self._ensure_loaded()
        assert self.state is not None
        self.state.last_updated = _utc_ts()
        content = self._render_markdown(reason=reason)
        _ensure_dir(self.plan_path)
        self.plan_path.write_text(content, encoding="utf-8")

    # ---------- internals ----------
    def _ensure_loaded(self) -> None:
        if self.state is None:
            loaded = self._load_state()
            if loaded is None:
                # If no state exists, create a minimal one.
                self.state = PlanState(scenario_id="unknown")
            else:
                self.state = loaded

    def _bootstrap_from_tasks(self, scenario_id: str, tasks: List[Dict[str, str]]) -> PlanState:
        task_objs: List[PlanTask] = []
        for item in tasks:
            tid = str(item.get("task_id") or "")
            title = str(item.get("title") or "")
            if not tid or not title:
                continue
            task_objs.append(PlanTask(task_id=tid, title=title))
        return PlanState(scenario_id=scenario_id, tasks=task_objs, logs=[f"{_utc_ts()} plan initialized"])

    def _find_task(self, task_id: str) -> Optional[PlanTask]:
        assert self.state is not None
        for t in self.state.tasks:
            if t.task_id == task_id:
                return t
        return None

    def _render_markdown(self, reason: str = "") -> str:
        assert self.state is not None
        lines: List[str] = []
        lines.append(f"# Plan for scenario: {self.state.scenario_id}")
        lines.append("")
        lines.append("## 0. Meta")
        lines.append(f"- CreatedAt: {self.state.created_at}")
        lines.append(f"- LastUpdated: {self.state.last_updated}")
        if reason:
            lines.append(f"- RefreshReason: {reason}")
        lines.append("")
        lines.append("## 1. Tasks (report-oriented)")
        for t in self.state.tasks:
            checkbox = "[ ]"
            if t.status == "done":
                checkbox = "[x]"
            elif t.status == "doing":
                checkbox = "[~]"
            note = f" — {t.note}" if t.note else ""
            lines.append(f"- {checkbox} ({t.task_id}) {t.title}{note}")
        lines.append("")
        lines.append("## 2. Progress log")
        for item in self.state.logs[-50:]:
            lines.append(f"- {item}")
        lines.append("")
        # Embedded machine state (single line)
        embedded = json.dumps(self.state.as_dict(), ensure_ascii=False)
        lines.append(f"<!-- PLAN_STATE: {embedded} -->")
        lines.append("")
        return "\n".join(lines)

    def _load_state(self) -> Optional[PlanState]:
        if not self.plan_path.exists():
            return None
        raw = self.plan_path.read_text(encoding="utf-8", errors="ignore")
        marker = "<!-- PLAN_STATE:"
        start = raw.rfind(marker)
        if start == -1:
            return None
        end = raw.find("-->", start)
        if end == -1:
            return None
        payload = raw[start + len(marker): end].strip()
        try:
            data = json.loads(payload)
            tasks = [
                PlanTask(
                    task_id=str(t.get("task_id")),
                    title=str(t.get("title")),
                    status=str(t.get("status", "todo")),
                    note=str(t.get("note", "")),
                    updated_at=str(t.get("updated_at", _utc_ts())),
                )
                for t in (data.get("tasks") or [])
            ]
            logs = [str(x) for x in (data.get("logs") or [])]
            return PlanState(
                scenario_id=str(data.get("scenario_id") or "unknown"),
                created_at=str(data.get("created_at") or _utc_ts()),
                last_updated=str(data.get("last_updated") or _utc_ts()),
                tasks=tasks,
                logs=logs,
            )
        except Exception:
            return None
