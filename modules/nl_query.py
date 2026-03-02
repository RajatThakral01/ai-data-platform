"""
nl_query.py – Natural-language → Pandas code execution engine.

Takes a plain-English question and a DataFrame, sends the question to a
locally running Ollama LLM (via ``llm.ollama_client``), extracts the
generated Pandas code, executes it in a sandboxed namespace with a
configurable timeout, and returns both the result and the generated code.

Usage:
    from modules.nl_query import ask

    answer = ask(df, "What are the top 5 products by revenue?")
    print(answer["result"])
    print(answer["code"])
"""

from __future__ import annotations

import collections
import datetime
import decimal
import fractions
import functools
import itertools
import json
import logging
import math
import operator
import re
import statistics
import string
import textwrap
import threading
from typing import Any

import numpy as np
import pandas as pd

from llm.ollama_client import OllamaClient
from llm.prompts import nl_to_pandas_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT_SECONDS: int = 30
DEFAULT_DF_NAME: str = "df"

# Stdlib modules that are safe to expose inside exec()
_ALLOWED_MODULES: dict[str, Any] = {
    "collections": collections,
    "datetime": datetime,
    "decimal": decimal,
    "fractions": fractions,
    "functools": functools,
    "itertools": itertools,
    "json": json,
    "math": math,
    "operator": operator,
    "re": re,
    "statistics": statistics,
    "string": string,
}


def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
    """Restricted ``__import__`` that only allows whitelisted stdlib modules."""
    if name in _ALLOWED_MODULES:
        return _ALLOWED_MODULES[name]
    raise ImportError(
        f"Importing '{name}' is not allowed in the sandbox. "
        f"Allowed modules: {sorted(_ALLOWED_MODULES)}"
    )


# Builtins explicitly allowed inside exec()
_SAFE_BUILTINS: dict[str, Any] = {
    "__builtins__": {
        # Arithmetic / type functions
        "abs": abs,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "frozenset": frozenset,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "print": print,
        "range": range,
        "reversed": reversed,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "type": type,
        "zip": zip,
        # Allow whitelisted imports
        "__import__": _safe_import,
        # Exceptions (needed so user code can raise/catch)
        "Exception": Exception,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "AttributeError": AttributeError,
        "ImportError": ImportError,
        "None": None,
        "True": True,
        "False": False,
    }
}


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class NLQueryError(Exception):
    """Base exception for the nl_query module."""


class CodeGenerationError(NLQueryError):
    """Raised when the LLM fails to produce valid Python code."""


class CodeExecutionError(NLQueryError):
    """Raised when the generated code fails during execution."""


class ExecutionTimeoutError(NLQueryError):
    """Raised when code execution exceeds the allowed timeout."""


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------
_CODE_BLOCK_RE = re.compile(
    r"```(?:python)?\s*\n(.*?)```",
    re.DOTALL,
)


def extract_code(llm_response: str) -> str:
    """Extract Python code from an LLM response.

    Tries fenced code blocks first (```python ... ```), then falls back
    to the full response if no block is found.

    Raises:
        CodeGenerationError: if the response is empty or no code found.
    """
    if not llm_response or not llm_response.strip():
        raise CodeGenerationError("LLM returned an empty response.")

    matches = _CODE_BLOCK_RE.findall(llm_response)
    if matches:
        # Pick the longest code block (most likely the main solution)
        code = max(matches, key=len).strip()
        if code:
            return code

    # Fallback: treat whole response as code (strip markdown noise)
    stripped = llm_response.strip()
    # Remove leading ```python and trailing ```
    stripped = re.sub(r"^```(?:python)?", "", stripped)
    stripped = re.sub(r"```$", "", stripped).strip()

    if not stripped:
        raise CodeGenerationError(
            "Could not extract Python code from the LLM response."
        )
    return stripped


# ---------------------------------------------------------------------------
# Safe execution
# ---------------------------------------------------------------------------
def _execute_code(
    code: str,
    df: pd.DataFrame,
    df_name: str,
    timeout: int,
) -> Any:
    """Execute *code* in a restricted namespace and return ``result``.

    The namespace contains *df* (under *df_name*), ``pd``, ``np``, and a
    restricted set of builtins.  ``exec()`` is run in a daemon thread so
    we can enforce a wall-clock *timeout*.

    Raises:
        CodeExecutionError: on runtime errors inside the generated code.
        ExecutionTimeoutError: if execution exceeds *timeout* seconds.
    """
    namespace: dict[str, Any] = {
        **_SAFE_BUILTINS,
        df_name: df.copy(),  # give exec a copy to prevent mutation
        "pd": pd,
        "np": np,
        # Pre-inject allowed stdlib modules so code can use them directly
        **_ALLOWED_MODULES,
    }

    exec_error: list[Exception] = []

    def _run() -> None:
        try:
            exec(code, namespace)  # noqa: S102 – intentional exec
        except Exception as exc:
            exec_error.append(exc)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        raise ExecutionTimeoutError(
            f"Code execution exceeded the {timeout}s timeout. "
            "The code may contain an infinite loop."
        )

    if exec_error:
        raise CodeExecutionError(
            f"Generated code raised an error:\n\n"
            f"  {type(exec_error[0]).__name__}: {exec_error[0]}\n\n"
            f"Code:\n{textwrap.indent(code, '  ')}"
        ) from exec_error[0]

    if "result" not in namespace:
        raise CodeExecutionError(
            "Generated code did not assign a variable called `result`.\n\n"
            f"Code:\n{textwrap.indent(code, '  ')}"
        )

    return namespace["result"]


# ---------------------------------------------------------------------------
# EDA summary builder (lightweight, for the prompt)
# ---------------------------------------------------------------------------
def _quick_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Build a minimal EDA-style summary dict for prompt generation.

    This avoids importing the full ``modules.eda`` module and the Plotly
    dependency.  The dict shape matches what ``llm.prompts.nl_to_pandas_prompt``
    expects.
    """
    desc_stats: dict[str, Any] = {}

    for col in df.select_dtypes(include="number").columns:
        desc_stats[col] = {"mean": float(df[col].mean())}

    for col in df.select_dtypes(include=["object", "category", "bool"]).columns:
        desc_stats[col] = {"unique": int(df[col].nunique())}

    missing_cols: dict[str, dict[str, Any]] = {}
    for col in df.columns:
        cnt = int(df[col].isna().sum())
        pct = round(cnt / len(df) * 100, 2) if len(df) > 0 else 0.0
        missing_cols[col] = {"count": cnt, "percentage": pct}

    return {
        "descriptive_stats": desc_stats,
        "missing_values": {
            "total_missing": int(df.isna().sum().sum()),
            "columns": missing_cols,
        },
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def ask(
    df: pd.DataFrame,
    question: str,
    *,
    model: str = "mistral",
    host: str = "http://localhost:11434",
    temperature: float = 0.2,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    df_name: str = DEFAULT_DF_NAME,
) -> dict[str, Any]:
    """Answer a natural-language *question* about *df* using an LLM.

    End-to-end pipeline:
        1. Build a prompt describing *df*'s schema.
        2. Send the prompt to the Ollama LLM.
        3. Extract Python code from the response.
        4. Execute the code in a sandboxed namespace.
        5. Return the result alongside the generated code.

    Parameters
    ----------
    df : pd.DataFrame
        The data to query.
    question : str
        A natural-language question.
    model : str
        Ollama model name (default ``"mistral"``).
    host : str
        Ollama server URL (default ``"http://localhost:11434"``).
    temperature : float
        Sampling temperature (default ``0.2`` for deterministic code).
    timeout : int
        Maximum seconds for code execution (default ``30``).
    df_name : str
        Variable name injected into the exec namespace (default ``"df"``).

    Returns
    -------
    dict[str, Any]
        Keys:
            ``question``  – original question.
            ``code``      – generated Python code string.
            ``result``    – execution output (the value of ``result``).
            ``success``   – ``True`` if everything worked.
            ``error``     – error message string, or ``None``.

    Raises
    ------
    ValueError
        If *df* or *question* is invalid.
    """
    # ---- input validation --------------------------------------------------
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError(f"Expected a pandas DataFrame, got {type(df).__name__}.")
    if df.empty:
        raise ValueError("Cannot query an empty DataFrame.")
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    summary = _quick_summary(df)
    prompt = nl_to_pandas_prompt(summary, question, dataframe_name=df_name)

    # ---- call LLM ----------------------------------------------------------
    logger.info("Sending question to LLM: %s", question)
    try:
        client = OllamaClient(
            model=model,
            host=host,
            system_prompt=(
                "You are a Python data-analysis expert. "
                "Return ONLY executable Python code in a fenced code block. "
                "Always store the final answer in a variable called `result`."
            ),
            temperature=temperature,
        )
        llm_response = client.query(prompt)
    except Exception as exc:
        return {
            "question": question,
            "code": None,
            "result": None,
            "success": False,
            "error": f"LLM error: {exc}",
        }

    # ---- extract code ------------------------------------------------------
    try:
        code = extract_code(llm_response)
    except CodeGenerationError as exc:
        return {
            "question": question,
            "code": None,
            "result": None,
            "success": False,
            "error": str(exc),
        }

    # ---- execute code ------------------------------------------------------
    logger.info("Executing generated code:\n%s", code)
    try:
        result = _execute_code(code, df, df_name, timeout)
    except (CodeExecutionError, ExecutionTimeoutError) as exc:
        return {
            "question": question,
            "code": code,
            "result": None,
            "success": False,
            "error": str(exc),
        }

    logger.info("Query answered successfully.")
    return {
        "question": question,
        "code": code,
        "result": result,
        "success": True,
        "error": None,
    }


def execute_generated_code(
    code: str,
    df: pd.DataFrame,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    df_name: str = DEFAULT_DF_NAME,
) -> dict[str, Any]:
    """Execute pre-existing code against *df* without calling the LLM.

    Useful when you already have the generated code (e.g. from a cached
    response or manual edit) and want to re-run it.

    Returns the same dict shape as :func:`ask`.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError(f"Expected a pandas DataFrame, got {type(df).__name__}.")
    if not code or not code.strip():
        raise ValueError("Code cannot be empty.")

    try:
        result = _execute_code(code, df, df_name, timeout)
    except (CodeExecutionError, ExecutionTimeoutError) as exc:
        return {
            "question": None,
            "code": code,
            "result": None,
            "success": False,
            "error": str(exc),
        }

    return {
        "question": None,
        "code": code,
        "result": result,
        "success": True,
        "error": None,
    }
