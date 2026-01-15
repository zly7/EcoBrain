"""multi_energy_agent package.

This package implements a report-first industrial-park agent system.

Design principles:
- Agent focuses on: description, report generation, Q&A interaction.
- Complex math / optimization is out-of-scope for agents. If optimization is needed,
  provide pre-computed results (CSV/Excel/JSON) and let the agent explain them.
"""

from .schemas import Stage, ResultEnvelope
from .runner import run_scenario

__all__ = [
    "Stage",
    "ResultEnvelope",
    "run_scenario",
]
