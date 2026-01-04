"""Utility wrapper that optionally calls OpenAI while providing an offline fallback."""

from __future__ import annotations

import os
from typing import Optional

try:  # pragma: no cover - importing optional dependency
    from openai import OpenAI
except Exception:  # pragma: no cover - degrade gracefully if SDK missing
    OpenAI = None  # type: ignore


class StructuredLLMClient:
    """Tiny helper that hides OpenAI wiring with a deterministic fallback."""

    def __init__(
        self, model: str = "gpt-4o-mini", temperature: float = 0.1, api_key: Optional[str] = None
    ) -> None:
        self.model = model
        self.temperature = temperature
        key = api_key or os.getenv("OPENAI_API_KEY")
        if OpenAI and key:
            self._client = OpenAI(api_key=key)
        else:
            self._client = None

    def markdown(self, system_prompt: str, user_prompt: str, fallback: str) -> str:
        if not self._client:
            return fallback
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            message = response.choices[0].message
            return message.content if hasattr(message, "content") else fallback
        except Exception:
            return fallback
