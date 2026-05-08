from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from session_store import get_session, update_session
import pandas as pd
import json
import math
import re
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from llm.client_factory import get_llm_response, GROQ_MODEL_LARGE, GROQ_MODEL_SMALL

router = APIRouter()

class InsightsRequest(BaseModel):
    session_id: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def clean_for_json(obj):
    """Recursively convert NaN/Infinity to None for JSON serialization."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(i) for i in obj]
    return obj


def _get_dataset_metadata(df: pd.DataFrame, eda_results: dict = None) -> dict:
    """Extract metadata from DataFrame for LLM prompts (no Streamlit dependency)."""
    base_meta = {
        "columns": df.columns.tolist(),
        "dtypes": [str(d) for d in df.dtypes],
        "rows": len(df),
        "missing_pct": round(df.isna().sum().sum() / df.size * 100, 2) if df.size > 0 else 0,
        "sample": df.head(5).to_dict(orient="records"),
        "numeric_cols": df.select_dtypes(include="number").columns.tolist(),
        "categorical_cols": df.select_dtypes(include=["object", "category"]).columns.tolist(),
    }
    if eda_results:
        base_meta["stats"] = eda_results.get("stats", {})
        base_meta["missing"] = eda_results.get("missing", {})
        base_meta["outliers"] = eda_results.get("outliers", {})
        base_meta["correlations"] = eda_results.get("correlations", {})
        base_meta["column_types"] = eda_results.get("column_types", {})
    else:
        numeric_df = df.select_dtypes(include="number")
        base_meta["stats"] = numeric_df.describe().round(2).to_dict() if not numeric_df.empty else {}
        base_meta["missing"] = {col: round(df[col].isna().mean() * 100, 1) for col in df.columns if df[col].isna().any()}
        base_meta["outliers"] = {}
        base_meta["correlations"] = numeric_df.corr().round(2).to_dict() if len(numeric_df.columns) >= 2 else {}
        base_meta["column_types"] = {
            "numeric": df.select_dtypes(include="number").columns.tolist(),
            "categorical": df.select_dtypes(include="object").columns.tolist(),
            "datetime": df.select_dtypes(include="datetime").columns.tolist(),
        }
    return base_meta


def format_value(val, col_name: str = "") -> str:
    """Format a numeric value into a human-readable K/M/B string."""
    if pd.isna(val):
        return "N/A"
    if isinstance(val, str):
        return val
    try:
        abs_val = abs(float(val))
    except (ValueError, TypeError):
        return str(val)

    is_neg = float(val) < 0
    sign = "-" if is_neg else ""
    c_lower = str(col_name).lower()

    is_fin = any(w in c_lower for w in [
        "sales", "revenue", "profit", "price", "cost",
        "amount", "fee", "income", "spend", "value"
    ])
    is_pct = any(w in c_lower for w in [
        "rate", "pct", "percent", "ratio", "churn", "discount"
    ])

    cur = "$" if is_fin else ""

    if is_pct and 0 <= abs_val <= 1.0:
        return f"{sign}{abs_val * 100:.1f}%"
    if abs_val >= 1_000_000_000:
        return f"{sign}{cur}{abs_val / 1_000_000_000:.1f}B".replace(".0B", "B")
    elif abs_val >= 1_000_000:
        return f"{sign}{cur}{abs_val / 1_000_000:.1f}M".replace(".0M", "M")
    elif abs_val >= 1_000:
        return f"{sign}{cur}{abs_val / 1_000:.1f}K".replace(".0K", "K")
    elif isinstance(val, int) or (isinstance(abs_val, float) and abs_val.is_integer()):
        return f"{sign}{cur}{int(abs_val):,}"
    else:
        return f"{sign}{cur}{abs_val:,.2f}"


# ---------------------------------------------------------------------------
# Step 1: Detect business context via LLM (standalone, no Streamlit)
# ---------------------------------------------------------------------------
def _detect_business_context(df: pd.DataFrame, meta: dict) -> dict:
    """Call LLM to detect business domain and context. Pure function, no Streamlit."""
    prompt = (
        f"Given this dataset with columns: {meta['columns']}\n"
        f"and sample data: {meta['sample']}\n"
        f"and basic stats: {meta['rows']} rows, dtypes: {meta['dtypes']}\n\n"
        f"Top correlations: {str(meta.get('correlations', {}))[:500]}\n"
        f"Missing value columns: {list(meta.get('missing', {}).keys())}\n\n"
        "Answer in JSON only:\n"
        "{\n"
        '  "domain": "e-commerce | telecom | retail | finance | hr | healthcare | marketing | logistics | other",\n'
        '  "business_entity": "what is one row? e.g. customer, order, employee, transaction, product",\n'
        '  "target_metric": "the most important column to optimize, e.g. Sales, Churn, Profit, Revenue",\n'
        '  "business_questions": [\n'
        '    "exact question 1 this business would want answered",\n'
        '    "exact question 2",\n'
        '    "exact question 3",\n'
        '    "exact question 4",\n'
        '    "exact question 5"\n'
        "  ],\n"
        '  "kpi_columns": {\n'
        '    "primary": "most important numeric column name",\n'
        '    "secondary": "second most important numeric column name",\n'
        '    "rate_metric": "column representing a rate/% if exists else null",\n'
        '    "volume_metric": "column representing count/volume if exists else null"\n'
        "  },\n"
        '  "avoid_columns": ["list of columns that are IDs, codes, indexes — not useful for charts"]\n'
        "}"
    )

    try:
        text, _ = get_llm_response(
            prompt, temperature=0.1, max_tokens=1000,
            groq_model=GROQ_MODEL_LARGE, module_name="data_insights"
        )
        text = text[text.find('{'):text.rfind('}') + 1]
        return json.loads(text)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Step 2: KPI extraction (pure pandas)
# ---------------------------------------------------------------------------
def _extract_kpis(df: pd.DataFrame, context: dict) -> list[dict]:
    kpi_dict = context.get("kpi_columns", {})
    raw_kpis = []

    primary = kpi_dict.get("primary")
    secondary = kpi_dict.get("secondary")
    rate_o = kpi_dict.get("rate_metric")
    vol_o = kpi_dict.get("volume_metric")

    if primary and primary in df.columns:
        raw_kpis.append({"name": f"Total {primary}", "column": primary, "calculation": "sum"})
    if secondary and secondary in df.columns:
        raw_kpis.append({"name": f"Total {secondary}", "column": secondary, "calculation": "sum"})
    if primary and primary in df.columns:
        raw_kpis.append({"name": f"Avg {primary}", "column": primary, "calculation": "mean"})

    if rate_o and rate_o in df.columns:
        raw_kpis.append({"name": rate_o, "column": rate_o, "calculation": "mean"})
    elif vol_o and vol_o in df.columns:
        raw_kpis.append({"name": f"Total {vol_o}", "column": vol_o, "calculation": "sum"})

    kpis = []
    for k in raw_kpis:
        try:
            col = k["column"]
            if k["calculation"] == "sum":
                val = df[col].sum()
            elif k["calculation"] == "mean":
                val = df[col].mean()
            else:
                val = df[col].sum()
            kpis.append({
                "label": " ".join(dict.fromkeys(k.get("name", "").split())).upper(),
                "value": float(val),
                "formatted_value": format_value(val, col),
                "delta": None,
            })
        except Exception:
            pass

    return kpis


# ---------------------------------------------------------------------------
# Step 3: Chart specs via LLM + data computation
# ---------------------------------------------------------------------------
def _validate_chart_spec(spec: dict, df: pd.DataFrame, avoid_cols: list) -> tuple[bool, dict]:
    """
    Validates and auto-corrects a chart spec from LLM.
    Returns (is_valid, corrected_spec).
    """
    x_col = spec.get("x_column")
    y_col = spec.get("y_column")
    chart_type = spec.get("chart_type", "bar")
    agg = spec.get("aggregation", "none")

    if not x_col or x_col not in df.columns:
        return False, spec

    if x_col in avoid_cols:
        return False, spec

    if y_col and y_col == x_col:
        return False, spec

    if y_col and y_col not in df.columns:
        spec["y_column"] = None
        y_col = None

    if chart_type in ["bar", "line", "scatter"] and y_col:
        if not pd.api.types.is_numeric_dtype(df[y_col]):
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            safe_numeric = [c for c in numeric_cols if c not in avoid_cols and c != x_col]
            if safe_numeric:
                spec["y_column"] = safe_numeric[0]
            else:
                return False, spec

    if chart_type in ["pie", "donut"]:
        unique_count = df[x_col].nunique()
        if unique_count > 10:
            spec["chart_type"] = "bar"
        elif unique_count > 8:
            pass

    if chart_type == "histogram":
        if not pd.api.types.is_numeric_dtype(df[x_col]):
            return False, spec
        spec["y_column"] = None

    if agg in ["sum", "mean"] and not spec.get("y_column"):
        spec["aggregation"] = "count"

    return True, spec


def _generate_charts(df: pd.DataFrame, meta: dict, context: dict) -> list[dict]:
    domain = context.get("domain", "general")
    entity = context.get("business_entity", "row")
    target_metric = context.get("target_metric", "key metric")
    avoid_cols = context.get("avoid_columns", [])
    b_qs = context.get("business_questions", [])

    chart_prompt = (
        f"You are a senior business analyst. This is a {domain} dataset "
        f"where each row represents a {entity}. "
        f"The business wants to optimize {target_metric}.\n\n"
        f"Column names: {meta['columns']}\n"
        f"Data types: {meta['dtypes']}\n"
        f"Sample rows: {meta['sample']}\n"
        f"Columns to AVOID (IDs/codes): {avoid_cols}\n\n"
        f"Key correlations found: {str(meta.get('correlations', {}))[:600]}\n"
        f"Outlier counts: {meta.get('outliers', {})}\n\n"
        "Generate exactly 5 chart specifications that answer these specific business questions:\n"
        f"{b_qs}\n\n"
        "Rules:\n"
        "- Each chart must directly answer one business question\n"
        f"- Only use columns from: {meta['columns']} minus {avoid_cols}\n"
        "- Choose chart type based on data:\n"
        "  * bar for category comparisons\n"
        "  * line for time series (if date column exists)\n"
        "  * scatter for relationships between 2 numeric columns\n"
        "  * pie/donut for composition (max 7 categories)\n"
        "  * histogram for distributions\n"
        "- If x column represents time or sequential numeric values with more than 15 unique values "
        "(like tenure_months, age, days), use chart_type: 'line' not 'bar'\n"
        "- For bar charts: use the categorical column as x, numeric as y\n"
        "- Aggregation: specify 'sum', 'mean', 'count', or 'none'\n\n"
        "Return ONLY this JSON array, no explanation. JSON format:\n"
        '[{\n'
        '  "chart_type": "bar",\n'
        '  "x_column": "exact column name",\n'
        '  "y_column": "exact column name",\n'
        '  "color_column": null,\n'
        '  "aggregation": "sum",\n'
        '  "title": "descriptive title",\n'
        '  "business_question": "which question this answers",\n'
        '  "insight_hint": "what pattern to look for"\n'
        '}]'
    )

    try:
        chart_res, _ = get_llm_response(
            chart_prompt, temperature=0.2, max_tokens=1500,
            groq_model=GROQ_MODEL_LARGE, module_name="data_insights"
        )
        chart_res = chart_res[chart_res.find('['):chart_res.rfind(']') + 1]
        specs = json.loads(chart_res)
    except Exception:
        specs = []

    chart_outputs = []
    for spec in specs[:5]:
        is_valid, spec = _validate_chart_spec(spec, df, avoid_cols)
        if not is_valid:
            continue

        chart_type = spec.get("chart_type", "bar")
        x_col = spec.get("x_column")
        y_col = spec.get("y_column")
        agg = spec.get("aggregation", "none")

        plot_df = df.copy()

        # Aggregation
        if agg in ["sum", "mean", "count"] and y_col and y_col in plot_df.columns:
            if agg == "sum":
                plot_df = plot_df.groupby(x_col)[y_col].sum().reset_index()
            elif agg == "mean":
                plot_df = plot_df.groupby(x_col)[y_col].mean().reset_index()
            elif agg == "count":
                plot_df = plot_df.groupby(x_col)[y_col].count().reset_index()

        # Truncate categorical to top 15
        if y_col and y_col in plot_df.columns:
            if not pd.api.types.is_numeric_dtype(plot_df[x_col]):
                plot_df = plot_df.sort_values(y_col, ascending=False).head(15)

        cols_to_check = [x_col] + ([y_col] if y_col and y_col in plot_df.columns else [])
        plot_df = plot_df.dropna(subset=cols_to_check)

        data_res = []
        if y_col and y_col in plot_df.columns:
            for _, row in plot_df.iterrows():
                x_val = row[x_col]
                y_val = row[y_col]
                # Convert numpy types to native Python types
                if hasattr(x_val, 'item'):
                    x_val = x_val.item()
                if hasattr(y_val, 'item'):
                    y_val = y_val.item()
                data_res.append({"x": x_val, "y": y_val})
        else:
            for _, row in plot_df.iterrows():
                x_val = row[x_col]
                if hasattr(x_val, 'item'):
                    x_val = x_val.item()
                data_res.append({"x": x_val, "y": None})

        chart_outputs.append({
            "chart_type": chart_type,
            "x_col": x_col,
            "y_col": y_col,
            "title": spec.get("title", f"{y_col} by {x_col}"),
            "business_question": spec.get("business_question", ""),
            "insight_hint": spec.get("insight_hint", ""),
            "data": data_res,
        })

    return chart_outputs


# ---------------------------------------------------------------------------
# Step 4: Executive summary via LLM
# ---------------------------------------------------------------------------
def _generate_executive_summary(meta: dict) -> str:
    prompt = (
        "You are a senior business analyst. Here is a dataset: "
        f"columns={meta['columns']}, dtypes={meta['dtypes']}, "
        f"sample={meta['sample']}, key stats={meta['rows']} rows, {meta['missing_pct']}% missing. "
        "Write a 2-sentence executive summary of what this dataset is about and what is the single "
        "most important business insight visible in the data. Be specific with numbers."
    )
    try:
        text, _ = get_llm_response(
            prompt, max_tokens=300,
            groq_model=GROQ_MODEL_SMALL, module_name="data_insights"
        )
        return text
    except Exception:
        return "AI processing failed to summarize dataset overview."


# ---------------------------------------------------------------------------
# Step 5: AI bullet insights via LLM
# ---------------------------------------------------------------------------
def _generate_ai_insights(domain: str, entity: str, kpis: list = None, charts: list = None, meta: dict = None) -> list[str]:
    kpi_summary = ""
    if kpis:
        kpi_lines = [f"- {k['label']}: {k['formatted_value']}" for k in kpis[:4]]
        kpi_summary = "Computed KPIs:\n" + "\n".join(kpi_lines)

    chart_summary = ""
    if charts:
        chart_lines = [
            f"- {c['title']} ({c['chart_type']}): {c.get('insight_hint','')}"
            for c in charts[:5]
        ]
        chart_summary = "Charts generated for:\n" + "\n".join(chart_lines)

    correlation_summary = ""
    if meta and meta.get("correlations"):
        corr_dict = meta["correlations"]
        pairs = []
        seen = set()
        for col1, others in corr_dict.items():
            if isinstance(others, dict):
                for col2, val in others.items():
                    if col1 != col2 and (col2, col1) not in seen:
                        try:
                            pairs.append((col1, col2, abs(float(val))))
                            seen.add((col1, col2))
                        except (TypeError, ValueError):
                            pass
        top_corr = sorted(pairs, key=lambda x: x[2], reverse=True)[:3]
        if top_corr:
            corr_lines = [f"- {a} vs {b}: r={v:.2f}" for a, b, v in top_corr]
            correlation_summary = "Strongest correlations:\n" + "\n".join(corr_lines)

    outlier_summary = ""
    if meta and meta.get("outliers"):
        outlier_cols = [f"{col} ({count} outliers)"
                        for col, count in meta["outliers"].items() if count > 0]
        if outlier_cols:
            outlier_summary = f"Outliers detected in: {', '.join(outlier_cols[:3])}"

    prompt = (
        "You are a senior business analyst presenting to the CEO. "
        f"Dataset: {domain} domain, each row represents a {entity}.\n\n"
        f"{kpi_summary}\n"
        f"{chart_summary}\n"
        f"{correlation_summary}\n"
        f"{outlier_summary}\n\n"
        "Using the specific numbers above, write 5 bullet point insights. "
        "Each must: start with an action emoji, reference specific numbers "
        "from the data above, explain business impact, and suggest one "
        "concrete action. Max 2 sentences each.\n"
        "IMPORTANT: Return plain text only. No XML tags, no HTML tags, "
        "no markdown. No <para>, no **bold**, no #headers. "
        "Just plain bullet points starting with an emoji.\n"
    )
    try:
        text, _ = get_llm_response(
            prompt, temperature=0.4, max_tokens=600,
            groq_model=GROQ_MODEL_SMALL, module_name="data_insights"
        )
        text = re.sub(r'<[^>]+>', '', text).replace('**', '')
        return [i.strip() for i in text.split('\n') if i.strip() and len(i.strip()) > 3]
    except Exception:
        return ["Unable to extract analytical points at this time."]


def _generate_correlation_chart(
    df: pd.DataFrame,
    target_metric: str,
    meta: dict,
    avoid_cols: list
) -> dict | None:
    """
    Generates a correlation bar chart showing how numeric columns
    correlate with the target metric. Pure pandas, no LLM needed.
    Returns a chart dict or None if not possible.
    """
    try:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        if len(numeric_cols) < 3:
            return None

        target_col = None
        for col in numeric_cols:
            if col.lower() == target_metric.lower():
                target_col = col
                break

        if not target_col:
            safe_cols = [c for c in numeric_cols if c not in avoid_cols]
            if not safe_cols:
                return None
            target_col = safe_cols[0]

        other_cols = [c for c in numeric_cols
                      if c != target_col and c not in avoid_cols]

        if len(other_cols) < 2:
            return None

        correlations = {}
        for col in other_cols:
            try:
                corr_val = df[target_col].corr(df[col])
                if not pd.isna(corr_val):
                    correlations[col] = round(float(corr_val), 3)
            except Exception:
                pass

        if not correlations:
            return None

        sorted_corr = sorted(
            correlations.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:8]

        chart_data = [{"x": col, "y": val} for col, val in sorted_corr]

        return {
            "chart_type": "bar",
            "x_col": "Feature",
            "y_col": f"Correlation with {target_col}",
            "title": f"Feature Correlation with {target_col}",
            "business_question": f"Which factors most influence {target_col}?",
            "insight_hint": "Positive bars increase target metric, "
                           "negative bars decrease it. "
                           "Longer bars = stronger relationship.",
            "data": chart_data,
            "is_correlation_chart": True,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------
@router.post("/insights")
def run_insights(req: InsightsRequest):
    session = get_session(req.session_id)
    if not session or "df" not in session:
        raise HTTPException(status_code=404, detail="Session or DataFrame not found")

    try:
        df = session["df"]
        if isinstance(df, (list, dict)):
            df = pd.DataFrame(df)
        eda_results = session.get("eda_results")
        meta = _get_dataset_metadata(df, eda_results=eda_results)

        # 1. Detect business context (standalone LLM call)
        context = _detect_business_context(df, meta)
        if not context:
            context = {
                "domain": "general",
                "business_entity": "rows",
                "target_metric": "count",
                "business_questions": [
                    "What is the distribution?",
                    "Are there anomalies?",
                ],
                "kpi_columns": {},
                "avoid_columns": [],
            }

        # 2. Extract KPIs
        kpis = _extract_kpis(df, context)

        # 3. Generate charts
        charts = _generate_charts(df, meta, context)

        # Add Python-generated correlation chart
        corr_chart = _generate_correlation_chart(
            df=df,
            target_metric=context.get("target_metric", ""),
            meta=meta,
            avoid_cols=context.get("avoid_columns", [])
        )
        if corr_chart:
            charts.append(corr_chart)

        # 4. Executive summary
        executive_summary = _generate_executive_summary(meta)

        # 5. AI bullet insights
        ai_insights = _generate_ai_insights(
            domain=context.get("domain", "general"),
            entity=context.get("business_entity", "row"),
            kpis=kpis,
            charts=charts,
            meta=meta,
        )

        response_payload = {
            "business_context": {
                "domain": context.get("domain", "general"),
                "business_entity": context.get("business_entity", "rows"),
                "target_metric": context.get("target_metric", "count"),
                "business_questions": context.get("business_questions", []),
            },
            "kpis": kpis,
            "charts": charts,
            "executive_summary": executive_summary,
            "ai_insights": ai_insights,
            "dashboard_url": None,
        }

        result_dict = clean_for_json(response_payload)

        update_session(req.session_id, "insights_results", result_dict)

        return result_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
