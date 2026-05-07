"""
Chart Plan Builder
Combines domain mapper + business questions + real pandas
computations to produce a validated, data-rich dashboard plan.
Pure Python — no LLM needed.
"""

from __future__ import annotations
import pandas as pd
import math
import json
from typing import Optional

from utils.domain_mapper import match_columns, get_avoid_columns
from utils.business_questions import get_applicable_questions


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(val) -> Optional[float]:
    """Convert a value to float, returning None if not possible."""
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _format_value(val, col_name: str = "") -> str:
    """
    Format numeric value into human-readable string.
    Replicates format_value from insights.py.
    """
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    try:
        abs_val = abs(float(val))
    except (TypeError, ValueError):
        return str(val)

    is_neg  = float(val) < 0
    sign    = "-" if is_neg else ""
    c_lower = str(col_name).lower()

    is_fin = any(w in c_lower for w in [
        "sales", "revenue", "profit", "price", "cost",
        "amount", "fee", "income", "spend", "value", "charges",
    ])
    is_pct = any(w in c_lower for w in [
        "rate", "pct", "percent", "ratio", "churn",
        "discount", "conversion", "ctr", "fraud",
    ])
    cur = "$" if is_fin else ""

    if is_pct and 0 <= abs_val <= 1.0:
        return f"{sign}{abs_val * 100:.1f}%"
    if abs_val >= 1_000_000_000:
        return f"{sign}{cur}{abs_val/1_000_000_000:.1f}B"
    elif abs_val >= 1_000_000:
        return f"{sign}{cur}{abs_val/1_000_000:.1f}M"
    elif abs_val >= 1_000:
        return f"{sign}{cur}{abs_val/1_000:.1f}K"
    else:
        return f"{sign}{cur}{abs_val:,.2f}"


def _compute_chart_data(
    df: pd.DataFrame,
    x_col: str,
    y_col: Optional[str],
    chart_type: str,
    aggregation: str,
) -> list[dict]:
    """
    Compute chart data using pandas.
    Returns list of {x, y} dicts.
    """
    try:
        cols_to_use = [c for c in [x_col, y_col] if c]
        plot_df = df[cols_to_use].dropna()

        if chart_type == "histogram":
            counts, bin_edges = pd.cut(
                df[x_col].dropna(), bins=10, retbins=True
            )
            freq = counts.value_counts(sort=False)
            return [
                {"x": f"{bin_edges[i]:.1f}", "y": int(freq.iloc[i])}
                for i in range(len(freq))
            ]

        if y_col and y_col in plot_df.columns:
            if aggregation == "sum":
                plot_df = plot_df.groupby(x_col)[y_col].sum().reset_index()
            elif aggregation == "mean":
                plot_df = plot_df.groupby(x_col)[y_col].mean().round(2).reset_index()
            elif aggregation == "count":
                plot_df = plot_df.groupby(x_col)[y_col].count().reset_index()

            if pd.api.types.is_numeric_dtype(plot_df.get(y_col, pd.Series())):
                plot_df = plot_df.sort_values(y_col, ascending=False)
            plot_df = plot_df.head(15)

            result = []
            for _, row in plot_df.iterrows():
                x_val = row[x_col]
                y_val = row[y_col]
                x_val = x_val.item() if hasattr(x_val, "item") else x_val
                y_val = _safe_float(y_val)
                result.append({"x": x_val, "y": y_val})
            return result

        else:
            vc = df[x_col].value_counts().head(10)
            return [
                {"x": str(k), "y": int(v)}
                for k, v in vc.items()
            ]

    except Exception:
        return []


def _compute_kpi_value(
    df: pd.DataFrame,
    col: str,
    chart_type: str,
    kpi_label: str,
) -> Optional[dict]:
    """
    Compute a single KPI card value from a column.
    Returns KPI dict or None.
    """
    try:
        if chart_type == "donut" or chart_type == "pie":
            vc = df[col].value_counts(normalize=True)
            positive_keys = ["yes", "true", "1", "churned", "fraud",
                             "left", "attrition"]
            pos_rate = None
            for k in vc.index:
                if str(k).lower() in positive_keys:
                    pos_rate = vc[k]
                    break
            if pos_rate is None:
                pos_rate = vc.iloc[0]
            val = float(pos_rate)
            return {
                "label":           kpi_label.upper(),
                "value":           val,
                "formatted_value": f"{val * 100:.1f}%",
                "delta":           None,
            }
        else:
            if pd.api.types.is_numeric_dtype(df[col]):
                val = float(df[col].sum())
                return {
                    "label":           kpi_label.upper(),
                    "value":           val,
                    "formatted_value": _format_value(val, col),
                    "delta":           None,
                }
    except Exception:
        pass
    return None


# ── Main builder ──────────────────────────────────────────────────────────────

def build_plan(
    df: pd.DataFrame,
    domain: str,
    eda_results: Optional[dict] = None,
    insights_results: Optional[dict] = None,
    max_charts: int = 6,
) -> dict:
    """
    Build a complete, validated dashboard plan from a DataFrame.

    Priority:
    1. If insights_results exists — extract its plan directly
    2. Otherwise — build from domain_mapper + business_questions

    Returns:
    {
        "domain":             str,
        "source":             "insights" | "planner",
        "avoid_cols":         list[str],
        "matched_columns":    dict,
        "kpis":               list[dict],
        "charts":             list[dict],
        "business_questions": list[str],
    }
    """

    # ── Path 1: Use existing insights_results ─────────────────────────────────
    if insights_results:
        try:
            biz_ctx = insights_results.get("business_context", {})
            return {
                "domain":             biz_ctx.get("domain", domain),
                "source":             "insights",
                "avoid_cols":         [],
                "matched_columns":    {},
                "kpis":               insights_results.get("kpis", []),
                "charts":             insights_results.get("charts", []),
                "business_questions": biz_ctx.get("business_questions", []),
                "target_metric":      biz_ctx.get("target_metric", ""),
                "executive_summary":  insights_results.get(
                                          "executive_summary", ""),
            }
        except Exception:
            pass

    # ── Path 2: Build from domain mapper + business questions ─────────────────
    df_columns   = list(df.columns)
    avoid_cols   = get_avoid_columns(df_columns)
    matched_cols = match_columns(domain, df_columns, avoid_cols)
    questions    = get_applicable_questions(domain, matched_cols, max_charts)

    kpis   = []
    charts = []
    seen_kpi_labels = set()

    for q in questions:
        x_role = q["x_role"]
        y_role = q.get("y_role")

        x_col = matched_cols.get(x_role)
        y_col = matched_cols.get(y_role) if y_role else None

        if not x_col or x_col not in df.columns:
            continue

        if y_role and (not y_col or y_col not in df.columns):
            continue

        data = _compute_chart_data(
            df=df,
            x_col=x_col,
            y_col=y_col,
            chart_type=q["chart_type"],
            aggregation=q["aggregation"],
        )

        if not data:
            continue

        chart_id = f"chart_{len(charts) + 1}"
        charts.append({
            "chart_type":        q["chart_type"],
            "x_col":             x_col,
            "y_col":             y_col,
            "title":             q["title"],
            "business_question": q["question"],
            "insight_hint":      q["insight_hint"],
            "data":              data,
            "id":                chart_id,
        })

        if q.get("is_kpi") and q.get("kpi_label"):
            label = q["kpi_label"]
            if label not in seen_kpi_labels:
                kpi_col = y_col if y_col else x_col
                kpi = _compute_kpi_value(
                    df=df,
                    col=kpi_col,
                    chart_type=q["chart_type"],
                    kpi_label=label,
                )
                if kpi:
                    kpis.append(kpi)
                    seen_kpi_labels.add(label)

    kpis.insert(0, {
        "label":           "TOTAL RECORDS",
        "value":           float(len(df)),
        "formatted_value": f"{len(df):,}",
        "delta":           None,
    })

    return {
        "domain":             domain,
        "source":             "planner",
        "avoid_cols":         avoid_cols,
        "matched_columns":    {k: v for k, v in matched_cols.items() if v},
        "kpis":               kpis,
        "charts":             charts,
        "business_questions": [q["question"] for q in questions],
        "target_metric":      "",
        "executive_summary":  "",
    }