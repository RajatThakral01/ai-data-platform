"""
groq_client.py – Groq API client for the AI Data Platform.

Provides a ``GroqClient`` class with the same ``.query()`` interface as
:class:`OllamaClient` and :class:`GeminiClient`, enabling seamless
backend switching.  Optimised for fast code-generation tasks.

Usage:
    from llm.groq_client import GroqClient

    client = GroqClient(api_key="...", model="llama-3.3-70b-versatile")
    answer = client.query("Write Pandas code to get top 5 rows by revenue.")
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
DEFAULT_MODEL: str = "llama-3.3-70b-versatile"
DEFAULT_TEMPERATURE: float = 0.2
DEFAULT_SYSTEM_PROMPT: str = (
    "You are a helpful data-analysis assistant. "
    "Answer concisely and accurately."
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class GroqConnectionError(Exception):
    """Raised when the Groq API is unreachable or auth fails."""


class GroqRateLimitError(Exception):
    """Raised when Groq returns a 429 / rate-limit error."""


class GroqModelError(Exception):
    """Raised when the requested model is not available."""


class GroqQueryError(Exception):
    """Raised for any other error during query execution."""


# ---------------------------------------------------------------------------
# Client class
# ---------------------------------------------------------------------------
class GroqClient:
    """Wrapper around the Groq Python SDK with the same interface as
    :class:`OllamaClient`.

    Parameters
    ----------
    api_key : str | None
        Groq API key.  Falls back to ``GROQ_API_KEY`` env var.
    model : str
        Model name (default ``"llama-3.3-70b-versatile"``).
    system_prompt : str | None
        Optional system instruction prepended to every request.
    temperature : float
        Sampling temperature (default ``0.2`` for deterministic code).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        system_prompt: str | None = DEFAULT_SYSTEM_PROMPT,
        temperature: float = DEFAULT_TEMPERATURE,
        **kwargs: Any,
    ) -> None:
        self.model_name = model
        self.system_prompt = system_prompt
        self.temperature = temperature

        # Resolve API key
        self._api_key = api_key or os.getenv("GROQ_API_KEY", "")
        if not self._api_key:
            raise GroqConnectionError(
                "No Groq API key provided. Set GROQ_API_KEY in your "
                ".env file or pass api_key= directly."
            )

        try:
            from groq import Groq
            self._client = Groq(api_key=self._api_key)
        except Exception as exc:
            raise GroqConnectionError(
                f"Failed to initialise Groq client: {exc}"
            ) from exc

    # -- core query ----------------------------------------------------------
    def query(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Send *prompt* to Groq and return the response text.

        Parameters
        ----------
        prompt : str
            The user message.
        system_prompt : str | None
            Override the instance-level system prompt for this call.
        temperature : float | None
            Override the instance-level temperature for this call.
        max_tokens : int | None
            Maximum tokens in the response (default: model default).

        Returns
        -------
        str
            The assistant's reply.
        """
        if not prompt or not prompt.strip():
            raise GroqQueryError("Prompt cannot be empty.")

        sys_prompt = (
            system_prompt if system_prompt is not None else self.system_prompt
        )
        temp = temperature if temperature is not None else self.temperature

        messages: list[dict[str, str]] = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.info(
            "Querying Groq model='%s' (temp=%.2f) …",
            self.model_name, temp,
        )

        create_kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temp,
        }
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens

        try:
            response = self._client.chat.completions.create(**create_kwargs)
        except Exception as exc:
            error_msg = str(exc).lower()
            if "429" in error_msg or "rate" in error_msg or "quota" in error_msg:
                raise GroqRateLimitError(
                    f"Groq rate limit / quota exceeded: {exc}"
                ) from exc
            if "api key" in error_msg or "auth" in error_msg:
                raise GroqConnectionError(
                    f"Groq authentication failed: {exc}"
                ) from exc
            if "not found" in error_msg or "model" in error_msg:
                raise GroqModelError(
                    f"Model '{self.model_name}' is not available: {exc}"
                ) from exc
            raise GroqQueryError(
                f"Groq API error: {exc}"
            ) from exc

        # Extract text
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError) as exc:
            raise GroqQueryError(
                f"Failed to extract text from Groq response: {exc}"
            ) from exc

        if not content:
            raise GroqQueryError("Groq returned an empty response.")

        logger.info("Groq response received (%d chars).", len(content))
        return content

    def __repr__(self) -> str:
        return (
            f"GroqClient(model={self.model_name!r}, "
            f"temperature={self.temperature})"
        )
