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
    max_tokens: Optional[int] = None  # None means no limit (API default)
    run_context: Optional[RunContext] = None

    def __post_init__(self):
        # Allow override via environment variable
        env_max_tokens = os.getenv("OPENAI_MAX_TOKENS")
        if env_max_tokens:
            self.max_tokens = int(env_max_tokens)

    def markdown(self, system_prompt: str, user_prompt: str, fallback: str = "") -> str:
        """Return markdown text. If no LLM is available, return fallback."""

        def _log(record: Dict[str, Any]) -> None:
            if self.run_context:
                self.run_context.log_llm(record)

        # Use OPENAI_API_KEY only
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")

        if not api_key:
            print("[LLM WARNING] OPENAI_API_KEY not set, using fallback")
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

            # Initialize client with optional base_url for custom providers
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url

            print(f"[LLM] Calling {self.model} (max_tokens={self.max_tokens or 'unlimited'})...")
            client = OpenAI(**client_kwargs)

            # Build request kwargs
            request_kwargs = {
                "model": self.model,
                "temperature": self.temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            if self.max_tokens is not None:
                request_kwargs["max_tokens"] = self.max_tokens

            resp = client.chat.completions.create(**request_kwargs)
            content = (resp.choices[0].message.content or "").strip()
            print(f"[LLM] Response received, length: {len(content)} chars")
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
        except Exception as e:
            # Fallback path: try legacy openai package (if present), otherwise return fallback.
            print(f"[LLM WARNING] Modern OpenAI SDK failed: {str(e)}, trying legacy...")
            try:
                import openai  # type: ignore

                openai.api_key = api_key
                if base_url:
                    openai.api_base = base_url

                # Build request kwargs for legacy API
                legacy_kwargs = {
                    "model": self.model,
                    "temperature": self.temperature,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
                if self.max_tokens is not None:
                    legacy_kwargs["max_tokens"] = self.max_tokens

                resp = openai.ChatCompletion.create(**legacy_kwargs)  # type: ignore
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
            except Exception as e2:
                print(f"[LLM ERROR] LLM call failed: {str(e)}, {str(e2)}")
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
                        "error": f"llm_call_failed: {str(e)}, {str(e2)}",
                    }
                )
                return content
