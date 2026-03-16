"""
eda.py – Exploratory Data Analysis module for the AI Data Platform.

Produces descriptive statistics, missing-value analysis, a correlation
matrix, distribution & bar-chart figures (Plotly), and IQR-based outlier
detection.  Every result is returned in a single structured dictionary so
downstream consumers (dashboards, reports, LLM pipelines) can pick what
they need.

Usage:
    from modules.eda import run_eda

    results = run_eda(df)
    # results.keys() →
    #   "descriptive_stats", "missing_values", "correlation_matrix",
    #   "distribution_plots", "categorical_plots", "outliers"
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from llm.client_factory import get_llm_response, GROQ_MODEL_SMALL
from utils import chart_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds / configuration
# ---------------------------------------------------------------------------
_IQR_MULTIPLIER: float = 1.5
_MAX_CATEGORIES: int = 30  # skip bar charts when cardinality is too high
_PLOT_HEIGHT: int = 400
_PLOT_TEMPLATE: str = "plotly_white"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _select_columns(
    df: pd.DataFrame,
    kind: str,
) -> list[str]:
    """Return column names that match *kind* ('numeric' or 'categorical')."""
    if kind == "numeric":
        return df.select_dtypes(include="number").columns.tolist()
    return df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()


# ---------------------------------------------------------------------------
# Dataset Summary UI
# ---------------------------------------------------------------------------
def render_dataset_summary(df: pd.DataFrame):
    """Render a dataset summary card and AI description button."""
    st.markdown("### 📊 Dataset Summary")
    
    file_name = st.session_state.get("uploaded_name", "Unknown Dataset")
    rows, cols = df.shape
    
    domain_guess = file_name.rsplit('.', 1)[0].replace('-', ' ').replace('_', ' ').title()
    if domain_guess.lower() in ["unknown dataset", "data", "dataset"] or not domain_guess:
        domain_guess = "general"
        
    date_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    id_cols = [c for c in df.columns if "id" in str(c).lower()]
    target_col = df.columns[-1] if len(df.columns) > 0 else "Unknown"
    num_cols = df.select_dtypes(include="number").columns.tolist()
    
    total_cells = rows * cols
    missing_cells = df.isna().sum().sum()
    missing_pct = missing_cells / total_cells if total_cells > 0 else 0
    
    dup_count = df.duplicated().sum()
    dup_pct = dup_count / rows if rows > 0 else 0
    
    outlier_rows = 0
    if len(num_cols) > 0:
        outlier_mask = pd.Series(False, index=df.index)
        for c in num_cols:
            q1 = df[c].quantile(0.25)
            q3 = df[c].quantile(0.75)
            iqr = q3 - q1
            outlier_mask |= (df[c] < q1 - 1.5 * iqr) | (df[c] > q3 + 1.5 * iqr)
        outlier_rows = outlier_mask.sum()
    outlier_pct = outlier_rows / rows if rows > 0 else 0
    
    score = 100 - (missing_pct * 100) - (dup_pct * 100) - (outlier_pct * 50)
    quality_score = max(0, min(100, int(score)))
    
    with st.container(border=True):
        st.markdown(f"**Dataset:** {file_name} | **Size:** {rows:,} rows × {cols} columns")
        st.markdown(f"*This appears to be a {domain_guess} dataset with {rows:,} records and {cols} columns.*")
        
        st.markdown("**Key Columns Detected:**")
        st.markdown(f"- **Target (assumed):** `{target_col}`")
        st.markdown(f"- **Numeric:** {len(num_cols)} columns")
        st.markdown(f"- **Date:** {len(date_cols)} columns")
        st.markdown(f"- **ID:** {len(id_cols)} columns")
        
        color = "green" if quality_score >= 80 else "orange" if quality_score >= 60 else "red"
        st.markdown(f"**Data Quality Score:** :{color}[**{quality_score}/100**] "
                    f"*(Missing: {missing_pct:.1%}, Duplicates: {dup_pct:.1%}, Outliers: {outlier_pct:.1%})*")

    if "dataset_summary" not in st.session_state:
        st.session_state["dataset_summary"] = {}

    cache = st.session_state["dataset_summary"]

    if st.button("🤖 What is this data about?"):
        with st.spinner("Generating AI description..."):
            if file_name in cache:
                st.info(cache[file_name])
            else:
                col_info = ", ".join([f"{c} ({t})" for c, t in zip(df.columns, df.dtypes)])
                sample_data = df.head(3).to_string()
                prompt = (
                    "You are a data analyst. Based on these column names and sample rows, "
                    "write a 3-sentence plain English description of what this dataset is about, "
                    "what business domain it belongs to, and what kind of analysis would be most useful. "
                    "Be specific and concise.\n\n"
                    f"Columns: {col_info}\n\n"
                    f"Sample rows:\n{sample_data}"
                )
                try:
                    response_text, _ = get_llm_response(
                        prompt, 
                        max_tokens=200, 
                        groq_model=GROQ_MODEL_SMALL,
                        module_name="eda"
                    )
                    cache[file_name] = response_text
                    st.info(response_text)
                except Exception as e:
                    st.error(f"Failed to generate description: {e}")
    elif file_name in cache:
        st.info(cache[file_name])


# -- 1. Descriptive Statistics -----------------------------------------------
def _descriptive_stats(df: pd.DataFrame) -> dict[str, Any]:
    """Compute descriptive statistics for every column.

    Returns a nested dict: ``{column_name: {stat_name: value}}``.
    Numeric columns get mean / std / min / max / quartiles.
    Categorical columns get count / unique / top / freq.
    """
    stats: dict[str, Any] = {}

    num_cols = _select_columns(df, "numeric")
    if num_cols:
        desc = df[num_cols].describe().to_dict()
        for col, col_stats in desc.items():
            # Convert numpy types to native Python for JSON safety
            stats[col] = {k: _safe_value(v) for k, v in col_stats.items()}

    cat_cols = _select_columns(df, "categorical")
    if cat_cols:
        desc = df[cat_cols].describe().to_dict()
        for col, col_stats in desc.items():
            stats[col] = {k: _safe_value(v) for k, v in col_stats.items()}

    return stats


# -- 2. Missing-Value Analysis -----------------------------------------------
def _missing_value_analysis(df: pd.DataFrame) -> dict[str, Any]:
    """Analyse missing values per column.

    Returns:
        {
            "total_missing":  int,
            "columns": {
                column_name: {"count": int, "percentage": float},
                ...
            }
        }
    """
    total = int(df.isna().sum().sum())
    n_rows = len(df)
    columns: dict[str, dict[str, Any]] = {}

    for col in df.columns:
        cnt = int(df[col].isna().sum())
        pct = round(cnt / n_rows * 100, 2) if n_rows > 0 else 0.0
        columns[col] = {"count": cnt, "percentage": pct}

    return {"total_missing": total, "columns": columns}


# -- 3. Correlation Matrix ---------------------------------------------------
def _correlation_matrix(
    df: pd.DataFrame,
) -> dict[str, Any]:
    """Compute the Pearson correlation matrix for numeric columns.

    Returns:
        {
            "matrix": {col: {col: r, ...}, ...},   # nested dict
            "figure": plotly.graph_objects.Figure,
        }
    """
    num_cols = _select_columns(df, "numeric")
    if len(num_cols) < 2:
        logger.info("Fewer than 2 numeric columns – skipping correlation matrix.")
        return {"matrix": {}, "figure": None}

    corr = df[num_cols].corr()
    matrix_dict = {
        col: {k: _safe_value(v) for k, v in row.items()}
        for col, row in corr.to_dict().items()
    }

    fig = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            colorscale="RdBu_r",
            zmin=-1,
            zmax=1,
            text=np.round(corr.values, 2),
            texttemplate="%{text}",
            hovertemplate="(%{x}, %{y}): %{z:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(_PLOT_HEIGHT, 50 * len(num_cols))
    )
    fig = chart_config.apply_base_layout(fig, "Correlation Matrix")

    return {"matrix": matrix_dict, "figure": fig}


# -- 4. Distribution Plots (numeric) -----------------------------------------
def _distribution_plots(df: pd.DataFrame) -> dict[str, go.Figure | None]:
    """Create a histogram + KDE-style overlay for each numeric column.

    Returns ``{column_name: Figure}``.
    """
    figures: dict[str, go.Figure] = {}
    num_cols = _select_columns(df, "numeric")

    for col in num_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        
        if series.nunique() <= 1:
            figures[col] = None
            continue

        fig = px.histogram(
            series,
            x=col,
        )
        fig.update_layout(showlegend=False)
        fig = chart_config.apply_base_layout(fig, f"Distribution of {col}")
        figures[col] = fig

    return figures


# -- 5. Categorical Bar Charts -----------------------------------------------
def _categorical_plots(df: pd.DataFrame) -> dict[str, go.Figure]:
    """Create bar charts showing value counts for each categorical column.

    Columns with more than ``_MAX_CATEGORIES`` unique values are skipped
    to avoid unreadable charts.

    Returns ``{column_name: Figure}``.
    """
    figures: dict[str, go.Figure] = {}
    cat_cols = _select_columns(df, "categorical")

    for col in cat_cols:
        n_unique = df[col].nunique()
        if n_unique > _MAX_CATEGORIES:
            logger.info(
                "Skipping bar chart for '%s' (%d unique values > %d limit).",
                col,
                n_unique,
                _MAX_CATEGORIES,
            )
            continue

        counts = df[col].value_counts().reset_index()
        counts.columns = [col, "count"]

        fig = px.bar(
            counts,
            x=col,
            y="count",
        )
        fig.update_layout(xaxis_title=col, yaxis_title="Count")
        fig = chart_config.style_bar_chart(fig)
        fig = chart_config.add_bar_labels(fig)
        fig = chart_config.apply_base_layout(fig, f"Value Counts – {col}")
        figures[col] = fig

    return figures


# -- 6. Outlier Detection (IQR) ----------------------------------------------
def _detect_outliers_iqr(
    df: pd.DataFrame,
    multiplier: float = _IQR_MULTIPLIER,
) -> dict[str, Any]:
    """Detect outliers per numeric column using the IQR method.

    For each column returns:
        - lower_bound / upper_bound
        - outlier_count
        - outlier_indices  (list of integer index positions)

    Also returns:
        - total_outlier_rows: count of rows that have *at least one* outlier.

    Returns:
        {
            "columns": {col: {...}, ...},
            "total_outlier_rows": int,
        }
    """
    num_cols = _select_columns(df, "numeric")
    result: dict[str, Any] = {"columns": {}, "total_outlier_rows": 0}
    outlier_mask = pd.Series(False, index=df.index)

    for col in num_cols:
        series = df[col].dropna()
        if series.empty:
            result["columns"][col] = {
                "lower_bound": None,
                "upper_bound": None,
                "outlier_count": 0,
                "outlier_indices": [],
            }
            continue

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr

        col_outliers = (df[col] < lower) | (df[col] > upper)
        indices = df.index[col_outliers].tolist()

        result["columns"][col] = {
            "lower_bound": round(lower, 4),
            "upper_bound": round(upper, 4),
            "outlier_count": int(col_outliers.sum()),
            "outlier_indices": indices,
        }
        outlier_mask = outlier_mask | col_outliers

    result["total_outlier_rows"] = int(outlier_mask.sum())
    return result


# ---------------------------------------------------------------------------
# JSON-safe value converter
# ---------------------------------------------------------------------------
def _safe_value(val: Any) -> Any:
    """Convert numpy/pandas scalars to native Python types."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        v = float(val)
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, (np.ndarray,)):
        return val.tolist()
    if pd.isna(val):
        return None
    return val


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def run_eda(
    df: pd.DataFrame,
    *,
    iqr_multiplier: float = _IQR_MULTIPLIER,
    max_categories: int = _MAX_CATEGORIES,
) -> dict[str, Any]:
    """Run a full exploratory data analysis on *df*.

    Parameters
    ----------
    df : pd.DataFrame
        The input data (ideally already cleaned via ``data_loader.load_data``).
    iqr_multiplier : float, optional
        Multiplier for IQR-based outlier fences (default ``1.5``).
    max_categories : int, optional
        Skip categorical bar charts when a column has more unique values
        than this limit (default ``30``).

    Returns
    -------
    dict[str, Any]
        Keys:
            ``descriptive_stats``   – per-column statistics.
            ``missing_values``      – per-column missing counts & percentages.
            ``correlation_matrix``  – Pearson correlation dict + Plotly Figure.
            ``distribution_plots``  – ``{col: Figure}`` histograms.
            ``categorical_plots``   – ``{col: Figure}`` bar charts.
            ``outliers``            – IQR-based outlier report.

    Raises
    ------
    ValueError
        If *df* is ``None`` or not a DataFrame.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("Expected a pandas DataFrame, got %s." % type(df).__name__)
    if df.empty:
        raise ValueError("Cannot run EDA on an empty DataFrame.")

    logger.info("Starting EDA on DataFrame with shape %s.", df.shape)

    # Temporarily override module-level limit for this run
    global _MAX_CATEGORIES
    original_max = _MAX_CATEGORIES
    _MAX_CATEGORIES = max_categories

    try:
        results: dict[str, Any] = {
            "descriptive_stats": _descriptive_stats(df),
            "missing_values": _missing_value_analysis(df),
            "correlation_matrix": _correlation_matrix(df),
            "distribution_plots": _distribution_plots(df),
            "categorical_plots": _categorical_plots(df),
            "outliers": _detect_outliers_iqr(df, multiplier=iqr_multiplier),
        }
    finally:
        _MAX_CATEGORIES = original_max

    logger.info("EDA complete.")
    return results
