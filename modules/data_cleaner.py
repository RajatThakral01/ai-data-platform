"""
data_cleaner.py – Interactive data-cleaning utilities for the AI Data Platform.

Provides pure-logic helpers for each cleaning operation.  The Streamlit UI
is handled by ``app.py``; this module contains **no** Streamlit code.

Usage:
    from modules.data_cleaner import (
        detect_duplicates, remove_duplicates,
        detect_outliers_iqr, remove_outliers, cap_outliers,
        suggest_type_fixes, fix_column_type,
        build_before_after_summary,
    )
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Missing-value helpers
# ---------------------------------------------------------------------------
def fill_missing(
    df: pd.DataFrame,
    column: str,
    strategy: str,
    custom_value: Any = None,
) -> pd.DataFrame:
    """Fill missing values in *column* using the chosen *strategy*.

    Strategies: ``"drop"``, ``"mean"``, ``"median"``, ``"mode"``, ``"custom"``.
    """
    df = df.copy()
    if strategy == "drop":
        df = df.dropna(subset=[column]).reset_index(drop=True)
    elif strategy == "mean":
        df[column] = df[column].fillna(df[column].mean())
    elif strategy == "median":
        df[column] = df[column].fillna(df[column].median())
    elif strategy == "mode":
        mode_val = df[column].mode()
        if not mode_val.empty:
            df[column] = df[column].fillna(mode_val.iloc[0])
    elif strategy == "custom":
        df[column] = df[column].fillna(custom_value)
    return df


def missing_value_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return a summary of missing values per column."""
    counts = df.isna().sum()
    pcts = (counts / len(df) * 100).round(2)
    summary = pd.DataFrame({
        "Column": counts.index,
        "Missing": counts.values,
        "Percent": pcts.values,
    })
    return summary[summary["Missing"] > 0].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Duplicate helpers
# ---------------------------------------------------------------------------
def detect_duplicates(df: pd.DataFrame) -> int:
    """Return the number of fully-duplicated rows."""
    return int(df.duplicated().sum())


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop fully-duplicated rows."""
    return df.drop_duplicates().reset_index(drop=True)


# ---------------------------------------------------------------------------
# Outlier helpers (IQR method)
# ---------------------------------------------------------------------------
def detect_outliers_iqr(
    df: pd.DataFrame,
    column: str,
    factor: float = 1.5,
) -> dict[str, Any]:
    """Detect outliers in a numeric *column* using the IQR method.

    Returns dict with ``count``, ``lower_bound``, ``upper_bound``,
    ``outlier_indices``.
    """
    series = df[column].dropna()
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    mask = (df[column] < lower) | (df[column] > upper)
    return {
        "count": int(mask.sum()),
        "lower_bound": round(lower, 4),
        "upper_bound": round(upper, 4),
        "outlier_indices": df.index[mask].tolist(),
    }


def remove_outliers(
    df: pd.DataFrame,
    column: str,
    factor: float = 1.5,
) -> pd.DataFrame:
    """Remove rows where *column* value is an IQR outlier."""
    info = detect_outliers_iqr(df, column, factor)
    return df.drop(index=info["outlier_indices"]).reset_index(drop=True)


def cap_outliers(
    df: pd.DataFrame,
    column: str,
    factor: float = 1.5,
) -> pd.DataFrame:
    """Cap (clip) outlier values to the IQR bounds instead of removing."""
    df = df.copy()
    info = detect_outliers_iqr(df, column, factor)
    df[column] = df[column].clip(lower=info["lower_bound"], upper=info["upper_bound"])
    return df


# ---------------------------------------------------------------------------
# Data-type fixing
# ---------------------------------------------------------------------------
def suggest_type_fixes(df: pd.DataFrame) -> list[dict[str, str]]:
    """Detect columns where the inferred type may be wrong.

    Looks for object columns that are mostly numeric or mostly datetime.
    Returns a list of ``{"column": ..., "current": ..., "suggested": ...}``.
    """
    suggestions: list[dict[str, str]] = []
    for col in df.select_dtypes(include=["object"]).columns:
        non_null = df[col].dropna()
        if non_null.empty:
            continue

        # Try numeric
        numeric = pd.to_numeric(non_null, errors="coerce")
        if numeric.notna().sum() / len(non_null) >= 0.8:
            suggestions.append({
                "column": col,
                "current": "object (text)",
                "suggested": "numeric (float64)",
            })
            continue

        # Try datetime
        try:
            dt = pd.to_datetime(non_null, errors="coerce", infer_datetime_format=True)
            if dt.notna().sum() / len(non_null) >= 0.8:
                suggestions.append({
                    "column": col,
                    "current": "object (text)",
                    "suggested": "datetime",
                })
        except Exception:
            pass

    return suggestions


def fix_column_type(
    df: pd.DataFrame,
    column: str,
    target_type: str,
) -> pd.DataFrame:
    """Convert *column* to *target_type* (``"numeric"`` or ``"datetime"``)."""
    df = df.copy()
    if target_type == "numeric":
        df[column] = pd.to_numeric(df[column], errors="coerce")
    elif target_type == "datetime":
        df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Column dropping
# ---------------------------------------------------------------------------
def drop_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Drop the specified *columns* from *df*."""
    return df.drop(columns=columns, errors="ignore")


# ---------------------------------------------------------------------------
# Before / After summary
# ---------------------------------------------------------------------------
def build_before_after_summary(
    original: pd.DataFrame,
    cleaned: pd.DataFrame,
) -> dict[str, Any]:
    """Build a comparison dict showing changes between original and cleaned."""
    return {
        "original_rows": len(original),
        "cleaned_rows": len(cleaned),
        "rows_removed": len(original) - len(cleaned),
        "original_cols": original.shape[1],
        "cleaned_cols": cleaned.shape[1],
        "cols_removed": original.shape[1] - cleaned.shape[1],
        "original_missing": int(original.isna().sum().sum()),
        "cleaned_missing": int(cleaned.isna().sum().sum()),
        "original_duplicates": detect_duplicates(original),
        "cleaned_duplicates": detect_duplicates(cleaned),
    }


# ---------------------------------------------------------------------------
# AI Cleaning Suggestions
# ---------------------------------------------------------------------------
def get_ai_cleaning_suggestions(
    eda_summary: dict[str, Any],
) -> str | None:
    """Ask the LLM for cleaning recommendations based on the EDA summary.

    Uses 8b model (simple task) with 300-token cap.
    Returns the suggestion text or ``None`` on failure.
    """
    from llm.client_factory import get_llm_response, GROQ_MODEL_SMALL
    from llm.prompts import _compact_summary

    data = _compact_summary(eda_summary)

    prompt = (
        "Role: data analyst. Given this EDA summary, list cleaning recommendations.\n"
        "Cover: (1) columns to DROP (IDs, constants) (2) missing value strategy per column "
        "(3) outlier concerns (4) type fixes.\n"
        "Be specific with column names. Numbered list.\n\n"
        f"DATA:\n{data}"
    )

    try:
        text, _meta = get_llm_response(
            prompt,
            temperature=0.3,
            max_tokens=300,
            groq_model=GROQ_MODEL_SMALL,
        )
        return text
    except Exception as exc:
        logger.warning("AI cleaning suggestions failed: %s", exc)
        return None

