"""FastAPI service for multi_energy_agent.

Expose ``app`` so callers can run ``uvicorn multi_energy_agent.api.main:app``.
"""

from .main import app

__all__ = ["app"]
