"""Lightweight LLM client wrapper.

The project is designed to run even without an LLM (deterministic fallbacks).
If you configure OpenAI credentials, the client will attempt to generate better
markdown text; otherwise it returns the provided fallback.

NOTE:
- This agent system should NOT do heavy optimization in LLM.
- LLM is only used for narrative drafting (description/report/QA).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Any, Dict

from .utils.logging import RunContext


@dataclass
class StructuredLLMClient:
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "1800"))
    run_context: Optional[RunContext] = None

    def markdown(self, system_prompt: str, user_prompt: str, fallback: str = "") -> str:
        """Return markdown text. If no LLM is available, return fallback."""

        def _log(record: Dict[str, Any]) -> None:
            if self.run_context:
                self.run_context.log_llm(record)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            content = fallback or user_prompt
            _log(
                {
                    "event": "llm_markdown",
                    "llm_used": False,
                    "model": self.model,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "fallback_used": True,
                    "response": content,
                }
            )
            return content

        # Try the modern OpenAI python client first.
        try:
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = (resp.choices[0].message.content or "").strip()
            final = content or (fallback or user_prompt)
            _log(
                {
                    "event": "llm_markdown",
                    "llm_used": True,
                    "model": self.model,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "fallback_used": not bool(content),
                    "response": final,
                }
            )
            return final
        except Exception:
            # Fallback path: try legacy openai package (if present), otherwise return fallback.
            try:
                import openai  # type: ignore

                openai.api_key = api_key
                resp = openai.ChatCompletion.create(  # type: ignore
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                content = (resp["choices"][0]["message"]["content"] or "").strip()
                final = content or (fallback or user_prompt)
                _log(
                    {
                        "event": "llm_markdown",
                        "llm_used": True,
                        "model": self.model,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                        "fallback_used": not bool(content),
                        "response": final,
                    }
                )
                return final
            except Exception:
                content = fallback or user_prompt
                _log(
                    {
                        "event": "llm_markdown",
                        "llm_used": False,
                        "model": self.model,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                        "fallback_used": True,
                        "response": content,
                        "error": "llm_call_failed",
                    }
                )
                return content
