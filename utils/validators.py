"""
utils/validators.py – Lightweight input-validation helpers.

Shared utilities used across modules for common type / value checks.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def require_dataframe(obj: Any, *, name: str = "input") -> pd.DataFrame:
    """Raise ``ValueError`` if *obj* is not a non-empty DataFrame.

    Parameters
    ----------
    obj : Any
        The object to validate.
    name : str
        Label used in the error message (default ``"input"``).

    Returns
    -------
    pd.DataFrame
        The validated DataFrame (passthrough).

    Raises
    ------
    ValueError
        If *obj* is ``None``, not a DataFrame, or empty.
    """
    if obj is None or not isinstance(obj, pd.DataFrame):
        raise ValueError(
            f"Expected a pandas DataFrame for '{name}', "
            f"got {type(obj).__name__}."
        )
    if obj.empty:
        raise ValueError(f"'{name}' DataFrame is empty.")
    return obj


def require_column(df: pd.DataFrame, column: str) -> None:
    """Raise ``ValueError`` if *column* is not in *df*.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to check.
    column : str
        Column name to look for.

    Raises
    ------
    ValueError
        If *column* is not found.
    """
    if column not in df.columns:
        raise ValueError(
            f"Column '{column}' not found. "
            f"Available columns: {df.columns.tolist()}"
        )


def require_non_empty_string(value: Any, *, name: str = "value") -> str:
    """Raise ``ValueError`` if *value* is not a non-empty string.

    Returns the stripped string.
    """
    if not value or not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")
    return value.strip()
