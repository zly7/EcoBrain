"""Agent implementations exposed for the pipeline.

IMPORTANT:
- Agent count must be <= 4 (mentor requirement).
- Recommended 3-agent pipeline:
    1) DataIntakeAgent
    2) InsightSynthesisAgent
    3) ReportOrchestratorAgent
"""

from .data_intake import DataIntakeAgent
from .insight import InsightSynthesisAgent
from .report import ReportOrchestratorAgent

__all__ = [
    "DataIntakeAgent",
    "InsightSynthesisAgent",
    "ReportOrchestratorAgent",
]
