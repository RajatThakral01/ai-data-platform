"""
client_factory.py – Unified LLM routing for the AI Data Platform.

Single priority chain for ALL tasks:

    1. **Groq**   — fastest, highest free RPM
    2. **Gemini** (gemini-2.0-flash) — fallback if Groq fails
    3. **Ollama** (mistral) — final local fallback

Model tiering for Groq:
    - ``groq_model="llama-3.3-70b-versatile"`` for code generation (quality)
    - ``groq_model="llama-3.1-8b-instant"``     for narratives (speed)

All calls support ``max_tokens`` to cap response length.

Usage:
    from llm.client_factory import get_llm_response

    # Code gen (70b, unlimited tokens)
    text, meta = get_llm_response("Write pandas code...", max_tokens=300)

    # Narrative (8b, 300 token cap)
    text, meta = get_llm_response("Summarise...", groq_model="llama-3.1-8b-instant")
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
# Backend identifiers
# ---------------------------------------------------------------------------
BACKEND_OLLAMA = "ollama"
BACKEND_GEMINI = "gemini"
BACKEND_GROQ = "groq"
SUPPORTED_BACKENDS = {BACKEND_OLLAMA, BACKEND_GEMINI, BACKEND_GROQ}

# Default models
GROQ_MODEL_LARGE = "llama-3.3-70b-versatile"
GROQ_MODEL_SMALL = "llama-3.1-8b-instant"
DEFAULT_GROQ_MODEL = GROQ_MODEL_LARGE
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


# ---------------------------------------------------------------------------
# Low-level client factory (direct access)
# ---------------------------------------------------------------------------
def get_llm_client(
    backend: str = BACKEND_OLLAMA,
    *,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    host: str = "http://localhost:11434",
    api_key: str | None = None,
    **kwargs: Any,
) -> Any:
    """Create and return a raw LLM client for the specified backend.

    All clients expose a ``.query(prompt, ...)`` method.
    """
    backend = backend.lower().strip()

    if backend == BACKEND_OLLAMA:
        from llm.ollama_client import OllamaClient, DEFAULT_MODEL as _OL
        return OllamaClient(
            model=model or _OL,
            host=host,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs,
        )

    if backend == BACKEND_GEMINI:
        from llm.gemini_client import GeminiClient
        return GeminiClient(
            api_key=api_key or os.getenv("GEMINI_API_KEY"),
            model=model or DEFAULT_GEMINI_MODEL,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs,
        )

    if backend == BACKEND_GROQ:
        from llm.groq_client import GroqClient
        return GroqClient(
            api_key=api_key or os.getenv("GROQ_API_KEY"),
            model=model or DEFAULT_GROQ_MODEL,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs,
        )

    raise ValueError(
        f"Unknown backend '{backend}'. "
        f"Supported: {sorted(SUPPORTED_BACKENDS)}"
    )


# ---------------------------------------------------------------------------
# Unified priority-chain router
# ---------------------------------------------------------------------------
def get_llm_response(
    prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.3,
    max_tokens: int | None = None,
    groq_model: str = DEFAULT_GROQ_MODEL,
    host: str = "http://localhost:11434",
    module_name: str = "unknown",
) -> tuple[str, dict[str, Any]]:
    """Send *prompt* through the priority chain: Groq → Gemini → Ollama.

    Each backend is tried in order.  If a backend fails (rate limit, auth,
    network, etc.) the next one is attempted silently.  An error is raised
    only when **all three** fail.

    Parameters
    ----------
    prompt : str
        The text prompt.
    system_prompt : str | None
        Optional system instruction.
    temperature : float
        Sampling temperature (default ``0.3``).
    max_tokens : int | None
        Maximum tokens in response (caps cost & prevents runaway).
    groq_model : str
        Groq model to use — ``GROQ_MODEL_LARGE`` (70b, code) or
        ``GROQ_MODEL_SMALL`` (8b, narratives).  Default: 70b.
    host : str
        Ollama server URL (used only for the Ollama fallback).
    module_name : str
        Name of the requesting module, used for observability logging.

    Returns
    -------
    tuple[str, dict]
        ``(response_text, meta)`` where *meta* contains:
            ``backend_used``     – which backend answered.
            ``model_used``       – model name.
            ``fallback_warning`` – user-facing warning string or ``None``.
            ``backends_tried``   – list of backends attempted.
    """
    # Priority chain with chosen Groq model
    chain: list[tuple[str, str]] = [
        (BACKEND_GROQ, groq_model),
        (BACKEND_GEMINI, DEFAULT_GEMINI_MODEL),
        (BACKEND_OLLAMA, "mistral"),
    ]

    errors: list[tuple[str, str, str]] = []

    try:
        import uuid
        session_id = str(uuid.uuid4())
    except Exception:
        session_id = "unknown"

    import time
    from utils.llm_logger import log_call

    start_time = time.time()

    for backend, model in chain:
        try:
            client = get_llm_client(
                backend,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                host=host,
            )
            result = client.query(prompt, max_tokens=max_tokens)

            # Build fallback warning if we're not on the first choice
            fallback_warning = None
            if errors:
                tried = [e[0].title() for e in errors]
                fallback_warning = (
                    f"⚠️ {', '.join(tried)} unavailable — "
                    f"answered by {backend.title()} ({model})."
                )

            latency_ms = (time.time() - start_time) * 1000
            log_call(
                module_name=module_name,
                model_used=model,
                latency_ms=latency_ms,
                prompt=prompt,
                response=result,
                success=True,
                fallback_used=bool(errors),
                error_message=None,
                session_id=session_id
            )

            return result, {
                "backend_used": backend,
                "model_used": model,
                "fallback_warning": fallback_warning,
                "backends_tried": [e[0] for e in errors] + [backend],
            }

        except Exception as exc:
            logger.warning(
                "%s (%s) failed: %s – trying next backend",
                backend.title(), model, exc,
            )
            errors.append((backend, model, str(exc)))

    # All three failed
    latency_ms = (time.time() - start_time) * 1000
    error_details = "\n".join(
        f"  • {b.title()} ({m}): {e}" for b, m, e in errors
    )

    log_call(
        module_name=module_name,
        model_used="ALL_FAILED",
        latency_ms=latency_ms,
        prompt=prompt,
        response=None,
        success=False,
        fallback_used=True,
        error_message=error_details,
        session_id=session_id
    )

    raise RuntimeError(
        f"All LLM backends failed:\n{error_details}"
    )
