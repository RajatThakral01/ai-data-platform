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
def _build_summary_from_df(df: pd.DataFrame) -> dict[str, Any]:
    """Build a minimal EDA-like summary dict directly from a DataFrame.

    This allows AI suggestions to work even when Smart EDA hasn't been run.
    """
    desc_stats: dict[str, dict] = {}
    mv_cols: dict[str, dict] = {}

    for col in df.columns:
        series = df[col]
        missing_count = int(series.isna().sum())
        missing_pct = round(missing_count / len(df) * 100, 2) if len(df) else 0
        mv_cols[col] = {"count": missing_count, "percentage": missing_pct}

        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            desc_stats[col] = {
                "count": int(clean.count()),
                "mean": float(clean.mean()) if len(clean) else 0,
                "std": float(clean.std()) if len(clean) > 1 else 0,
                "min": float(clean.min()) if len(clean) else 0,
                "max": float(clean.max()) if len(clean) else 0,
            }
        else:
            desc_stats[col] = {
                "count": int(series.count()),
                "unique": int(series.nunique()),
                "top": str(series.mode().iloc[0]) if not series.mode().empty else "?",
            }

    return {
        "descriptive_stats": desc_stats,
        "missing_values": {
            "total_missing": int(df.isna().sum().sum()),
            "columns": mv_cols,
        },
        "correlation_matrix": {"matrix": {}},
        "outliers": {"total_outlier_rows": 0},
    }


def get_ai_cleaning_suggestions(
    df: pd.DataFrame,
    eda_summary: dict[str, Any] | None = None,
) -> tuple[str | None, str | None]:
    """Ask the LLM for cleaning recommendations.

    Parameters
    ----------
    df : pd.DataFrame
        The raw DataFrame (used to build stats if no EDA summary available).
    eda_summary : dict | None
        Pre-computed EDA summary.  If ``None``, stats are computed from *df*.

    Returns
    -------
    tuple[str | None, str | None]
        ``(suggestion_text, error_message)``
        — On success: ``("suggestions...", None)``
        — On failure: ``(None, "Groq: quota exceeded; Gemini: no key; ...")``
    """
    from llm.client_factory import get_llm_response, GROQ_MODEL_SMALL
    from llm.prompts import _compact_summary

    # Use EDA summary if available, otherwise compute from DataFrame
    summary = eda_summary if eda_summary else _build_summary_from_df(df)
    data = _compact_summary(summary)

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
            max_tokens=250,
            groq_model=GROQ_MODEL_SMALL,
            module_name="data_cleaner"
        )
        return text, None
    except RuntimeError as exc:
        # RuntimeError from client_factory means ALL backends failed
        logger.warning("AI cleaning suggestions – all backends failed: %s", exc)
        return None, str(exc)
    except Exception as exc:
        logger.warning("AI cleaning suggestions failed: %s", exc)
        return None, f"Unexpected error: {exc}"



# ---------------------------------------------------------------------------
# Auto Clean
# ---------------------------------------------------------------------------
def auto_clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Automatically clean the DataFrame for ML processing.

    Returns the cleaned DataFrame and a report dictionary detailing all steps.
    """
    cleaned = df.copy()
    report: dict[str, Any] = {}

    # 1. Drop unique identifiers
    id_cols = [col for col in cleaned.columns if (cleaned[col].nunique() == len(cleaned)) and (len(cleaned) > 0)]
    if id_cols:
        cleaned.drop(columns=id_cols, inplace=True)
        report["dropped_id_cols"] = id_cols

    # 2. Drop geographical columns
    geo_keywords = ['lat', 'long', 'zip', 'country', 'state', 'city', 'latitude', 'longitude', 'postal']
    geo_cols = [col for col in cleaned.columns if any(k in str(col).lower() for k in geo_keywords)]
    geo_cols = list(set(geo_cols))
    if geo_cols:
        cleaned.drop(columns=geo_cols, inplace=True)
        report["dropped_geo_cols"] = geo_cols

    # 3. Drop columns with > 70% missing
    threshold = 0.7 * len(cleaned)
    high_missing_cols = [col for col in cleaned.columns if cleaned[col].isna().sum() > threshold]
    if high_missing_cols:
        cleaned.drop(columns=high_missing_cols, inplace=True)
        report["dropped_missing_cols"] = high_missing_cols

    # 4. Fill missing: median for numeric, mode for categorical
    filled_missing = {}
    for col in cleaned.columns:
        missing_count = int(cleaned[col].isna().sum())
        if missing_count > 0:
            if pd.api.types.is_numeric_dtype(cleaned[col]):
                val = float(cleaned[col].median()) if pd.notna(cleaned[col].median()) else 0.0
                strategy = "median"
            else:
                mode_val = cleaned[col].mode()
                val = mode_val.iloc[0] if not mode_val.empty else "Unknown"
                strategy = "mode"
            cleaned[col] = cleaned[col].fillna(val)
            filled_missing[col] = {"count": missing_count, "strategy": strategy, "value": val}
    if filled_missing:
        report["filled_missing"] = filled_missing

    # 5. Remove duplicates
    dup_count = int(cleaned.duplicated().sum())
    if dup_count > 0:
        cleaned.drop_duplicates(inplace=True)
        cleaned.reset_index(drop=True, inplace=True)
        report["removed_duplicates"] = dup_count

    # 6. Cap outliers using IQR on all numeric
    capped_outliers = {}
    num_cols = cleaned.select_dtypes(include="number").columns
    for col in num_cols:
        q1 = cleaned[col].quantile(0.25)
        q3 = cleaned[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outliers_mask = (cleaned[col] < lower) | (cleaned[col] > upper)
        outliers_count = int(outliers_mask.sum())
        if outliers_count > 0:
            cleaned[col] = cleaned[col].clip(lower=lower, upper=upper)
            capped_outliers[col] = outliers_count
    if capped_outliers:
        report["capped_outliers"] = capped_outliers

    # 7. Label Encoding for categorical columns
    encoded_cols = []
    try:
        from sklearn.preprocessing import LabelEncoder
        for col in cleaned.select_dtypes(include=['object', 'category']).columns:
            le = LabelEncoder()
            cleaned[col] = le.fit_transform(cleaned[col].astype(str))
            encoded_cols.append(col)
    except ImportError:
        for col in cleaned.select_dtypes(include=['object', 'category']).columns:
            cleaned[col] = pd.factorize(cleaned[col])[0]
            encoded_cols.append(col)
    if encoded_cols:
        report["encoded_cols"] = encoded_cols

    return cleaned, report
