"""
ollama_client.py – Wrapper around the Ollama Python SDK for the
AI Data Platform.

Connects to a locally running Ollama server and exposes a simple
``query_model`` function that sends a prompt to **Mistral 7B** and
returns the response text.

Usage:
    from llm.ollama_client import query_model, OllamaClient

    # Quick one-shot call (uses module-level defaults):
    answer = query_model("Summarise this dataset for me.")

    # Or instantiate with custom settings:
    client = OllamaClient(model="mistral", host="http://localhost:11434")
    answer = client.query("Summarise this dataset for me.")
"""

from __future__ import annotations

import logging
from typing import Any

import ollama
from ollama import RequestError, ResponseError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
DEFAULT_MODEL: str = "mistral"
DEFAULT_HOST: str = "http://localhost:11434"
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_SYSTEM_PROMPT: str = (
    "You are a helpful data-analysis assistant. "
    "Answer concisely and accurately."
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class OllamaConnectionError(Exception):
    """Raised when the Ollama server is unreachable."""


class OllamaModelError(Exception):
    """Raised when the requested model is not available on the server."""


class OllamaQueryError(Exception):
    """Raised for any other error during query execution."""


# ---------------------------------------------------------------------------
# Client class
# ---------------------------------------------------------------------------
class OllamaClient:
    """Thin wrapper around :class:`ollama.Client` with sensible defaults.

    Parameters
    ----------
    model : str
        Ollama model tag (default ``"mistral"``).
    host : str
        Ollama server URL (default ``"http://localhost:11434"``).
    system_prompt : str | None
        Optional system message prepended to every conversation.
    temperature : float
        Sampling temperature (default ``0.7``).
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        system_prompt: str | None = DEFAULT_SYSTEM_PROMPT,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        self.model = model
        self.host = host
        self.system_prompt = system_prompt
        self.temperature = temperature

        try:
            self._client = ollama.Client(host=self.host)
        except Exception as exc:
            raise OllamaConnectionError(
                f"Failed to initialise Ollama client at {self.host}: {exc}"
            ) from exc

    # -- health check --------------------------------------------------------
    def is_server_running(self) -> bool:
        """Return ``True`` if the Ollama server responds to a list request."""
        try:
            self._client.list()
            return True
        except Exception:
            return False

    # -- model availability --------------------------------------------------
    def is_model_available(self) -> bool:
        """Return ``True`` if ``self.model`` is pulled locally."""
        try:
            models = self._client.list()
            available = [
                m.model for m in getattr(models, "models", [])
            ]
            # Ollama tags may include `:latest` suffix
            return any(
                self.model == name or name.startswith(f"{self.model}:")
                for name in available
            )
        except Exception:
            return False

    # -- core query ----------------------------------------------------------
    def query(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        """Send *prompt* to the model and return the response text.

        Parameters
        ----------
        prompt : str
            The user message.
        system_prompt : str | None
            Override the instance-level system prompt for this call.
        temperature : float | None
            Override the instance-level temperature for this call.
        **kwargs
            Extra keyword arguments forwarded to ``ollama.Client.chat``.

        Returns
        -------
        str
            The assistant's reply.

        Raises
        ------
        OllamaConnectionError
            If the Ollama server is not reachable.
        OllamaModelError
            If the requested model is not available.
        OllamaQueryError
            For any other query-time error.
        """
        if not prompt or not prompt.strip():
            raise OllamaQueryError("Prompt cannot be empty.")

        sys_prompt = system_prompt if system_prompt is not None else self.system_prompt
        temp = temperature if temperature is not None else self.temperature

        messages: list[dict[str, str]] = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.info("Querying model='%s' (temp=%.2f) …", self.model, temp)

        try:
            response = self._client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": temp},
                **kwargs,
            )
        except RequestError as exc:
            # RequestError typically means the server refused the connection
            raise OllamaConnectionError(
                f"Cannot reach Ollama at {self.host}. "
                "Is the Ollama server running? "
                f"(Start it with `ollama serve`)\n\nDetails: {exc}"
            ) from exc
        except ResponseError as exc:
            error_msg = str(exc).lower()
            if "not found" in error_msg or "model" in error_msg:
                raise OllamaModelError(
                    f"Model '{self.model}' is not available. "
                    f"Pull it first with `ollama pull {self.model}`.\n\n"
                    f"Details: {exc}"
                ) from exc
            raise OllamaQueryError(
                f"Ollama returned an error: {exc}"
            ) from exc
        except ConnectionError as exc:
            raise OllamaConnectionError(
                f"Connection to Ollama at {self.host} was refused. "
                "Is the server running?\n\n"
                f"Details: {exc}"
            ) from exc
        except Exception as exc:
            raise OllamaQueryError(
                f"Unexpected error while querying Ollama: {exc}"
            ) from exc

        # Extract the response text
        try:
            content = response.message.content
        except AttributeError:
            content = response.get("message", {}).get("content", "")

        if not content:
            raise OllamaQueryError(
                "Ollama returned an empty response. The model may have failed silently."
            )

        logger.info("Response received (%d chars).", len(content))
        return content

    def __repr__(self) -> str:
        return (
            f"OllamaClient(model={self.model!r}, host={self.host!r}, "
            f"temperature={self.temperature})"
        )


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------
_default_client: OllamaClient | None = None


def query_model(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    host: str = DEFAULT_HOST,
    system_prompt: str | None = DEFAULT_SYSTEM_PROMPT,
    temperature: float = DEFAULT_TEMPERATURE,
    **kwargs: Any,
) -> str:
    """One-shot helper: create (or reuse) an :class:`OllamaClient` and query it.

    Parameters and return value are identical to :meth:`OllamaClient.query`.
    """
    global _default_client

    if (
        _default_client is None
        or _default_client.model != model
        or _default_client.host != host
    ):
        _default_client = OllamaClient(
            model=model,
            host=host,
            system_prompt=system_prompt,
            temperature=temperature,
        )

    return _default_client.query(prompt, **kwargs)
