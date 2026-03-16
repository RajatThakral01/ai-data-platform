"""
gemini_client.py – Google Gemini API client for the AI Data Platform.

Provides a ``GeminiClient`` class with the same ``.query()`` interface as
:class:`OllamaClient`, enabling seamless backend switching.

Usage:
    from llm.gemini_client import GeminiClient

    client = GeminiClient(api_key="...", model="gemini-2.0-flash")
    answer = client.query("Summarise this dataset for me.")
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Force load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
DEFAULT_MODEL: str = "gemini-2.0-flash"
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_SYSTEM_PROMPT: str = (
    "You are a helpful data-analysis assistant. "
    "Answer concisely and accurately."
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class GeminiConnectionError(Exception):
    """Raised when the Gemini API is unreachable or auth fails."""


class GeminiModelError(Exception):
    """Raised when the requested model is not available."""


class GeminiRateLimitError(Exception):
    """Raised when Gemini returns a 429 / quota-exceeded error."""


class GeminiQueryError(Exception):
    """Raised for any other error during query execution."""


# ---------------------------------------------------------------------------
# Client class
# ---------------------------------------------------------------------------
class GeminiClient:
    """Wrapper around the Google Generative AI SDK with the same interface as
    :class:`OllamaClient`.

    Parameters
    ----------
    api_key : str | None
        Gemini API key.  Falls back to ``GEMINI_API_KEY`` env var.
    model : str
        Model name (default ``"gemini-2.0-flash"``).
    system_prompt : str | None
        Optional system instruction prepended to every request.
    temperature : float
        Sampling temperature (default ``0.7``).
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
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not self._api_key:
            raise GeminiConnectionError(
                "No Gemini API key provided. Set GEMINI_API_KEY in your "
                ".env file or pass api_key= directly."
            )

        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            self._genai = genai
            self._model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_prompt or None,
            )
        except Exception as exc:
            raise GeminiConnectionError(
                f"Failed to initialise Gemini client: {exc}"
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
        """Send *prompt* to Gemini and return the response text.

        Parameters
        ----------
        prompt : str
            The user message.
        system_prompt : str | None
            Override the instance-level system prompt for this call.
        temperature : float | None
            Override the instance-level temperature for this call.
        max_tokens : int | None
            Maximum tokens in the response.

        Returns
        -------
        str
            The assistant's reply.

        Raises
        ------
        GeminiQueryError
            For any query-time error.
        """
        if not prompt or not prompt.strip():
            raise GeminiQueryError("Prompt cannot be empty.")

        temp = temperature if temperature is not None else self.temperature

        # If caller overrides system_prompt, rebuild the model for this call
        effective_sys = (
            system_prompt if system_prompt is not None else self.system_prompt
        )
        if system_prompt is not None and system_prompt != self.system_prompt:
            model = self._genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=effective_sys or None,
            )
        else:
            model = self._model

        logger.info(
            "Querying Gemini model='%s' (temp=%.2f) …",
            self.model_name, temp,
        )

        gen_config = {"temperature": temp}
        if max_tokens is not None:
            gen_config["max_output_tokens"] = max_tokens

        try:
            response = model.generate_content(
                prompt,
                generation_config=self._genai.GenerationConfig(**gen_config),
            )
        except Exception as exc:
            error_msg = str(exc).lower()
            if "429" in error_msg or "quota" in error_msg or "rate" in error_msg or "resource_exhausted" in error_msg:
                raise GeminiRateLimitError(
                    f"Gemini rate limit / quota exceeded: {exc}"
                ) from exc
            if "api key" in error_msg or "auth" in error_msg:
                raise GeminiConnectionError(
                    f"Gemini authentication failed: {exc}"
                ) from exc
            if "not found" in error_msg or "model" in error_msg:
                raise GeminiModelError(
                    f"Model '{self.model_name}' is not available: {exc}"
                ) from exc
            raise GeminiQueryError(
                f"Gemini API error: {exc}"
            ) from exc

        # Extract text
        try:
            content = response.text
        except (AttributeError, ValueError) as exc:
            raise GeminiQueryError(
                f"Failed to extract text from Gemini response: {exc}"
            ) from exc

        if not content:
            raise GeminiQueryError(
                "Gemini returned an empty response."
            )

        logger.info("Gemini response received (%d chars).", len(content))
        return content

    def __repr__(self) -> str:
        return (
            f"GeminiClient(model={self.model_name!r}, "
            f"temperature={self.temperature})"
        )
