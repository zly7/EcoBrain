from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


def _tokyo_now() -> datetime:
    if ZoneInfo is None:
        return datetime.now()
    return datetime.now(ZoneInfo("Asia/Tokyo"))


def _timestamp() -> str:
    # YYYYMMDD_HHMMSS
    return _tokyo_now().strftime("%Y%m%d_%H%M%S")


def _repo_root() -> Path:
    # multi_energy_agent/utils/logging.py -> multi_energy_agent is 1 level up
    return Path(__file__).resolve().parents[1]


@dataclass
class RunContext:
    run_ts: str
    scenario_id: str
    output_dir: str
    logs_running_path: str
    logs_llm_direct_path: str
    pdf_dir: str
    logger: logging.Logger

    def log_llm(self, record: Dict[str, Any]) -> None:
        """Append one JSONL record to logs_llm_direct."""
        try:
            p = Path(self.logs_llm_direct_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            # never raise from logging
            pass


def init_run_context(
    scenario_id: str,
    *,
    output_dir: str,
    logs_running_dir: str = "log/running_log",
    logs_llm_direct_dir: str = "log/direct_llm_log",
    pdf_dir: str = "pdf",
) -> RunContext:
    """Create a per-run context with isolated log files.

    Log paths:
    - multi_energy_agent/log/direct_llm_log/<YYYYMMDD_HHMMSS>_<scenario>.jsonl
    - multi_energy_agent/log/running_log/<YYYYMMDD_HHMMSS>_<scenario>.log
    - multi_energy_agent/pdf/<scenario>/report.pdf
    """

    root = _repo_root()  # multi_energy_agent/
    ts = _timestamp()

    logs_running_path = str(root / logs_running_dir / f"{ts}_{scenario_id}.log")
    logs_llm_path = str(root / logs_llm_direct_dir / f"{ts}_{scenario_id}.jsonl")
    pdf_path = str(root / pdf_dir)

    # build a dedicated logger
    logger_name = f"multi_energy_agent.{scenario_id}.{ts}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # do not duplicate to root

    # Clear handlers if reused accidentally
    logger.handlers = []

    Path(logs_running_path).parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh = logging.FileHandler(logs_running_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)

    ctx = RunContext(
        run_ts=ts,
        scenario_id=scenario_id,
        output_dir=output_dir,
        logs_running_path=logs_running_path,
        logs_llm_direct_path=logs_llm_path,
        pdf_dir=pdf_path,
        logger=logger,
    )

    ctx.logger.info("=" * 60)
    ctx.logger.info("RunContext initialized")
    ctx.logger.info("  scenario_id: %s", scenario_id)
    ctx.logger.info("  timestamp: %s", ts)
    ctx.logger.info("  running_log: %s", logs_running_path)
    ctx.logger.info("  llm_log: %s", logs_llm_path)
    ctx.logger.info("  pdf_dir: %s", pdf_path)
    ctx.logger.info("=" * 60)
    return ctx


def get_run_context(state: Dict[str, Any]) -> Optional[RunContext]:
    ctx = state.get("run_context")
    return ctx if isinstance(ctx, RunContext) else None
