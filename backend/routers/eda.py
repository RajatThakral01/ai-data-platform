from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from session_store import get_session, update_session
import pandas as pd
import numpy as np
import math
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from llm.client_factory import get_llm_response, GROQ_MODEL_SMALL

router = APIRouter()


class EDARequest(BaseModel):
    session_id: str


def clean_for_json(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, np.floating):
        if math.isnan(float(obj)) or math.isinf(float(obj)):
            return None
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(i) for i in obj]
    return obj


def _compute_stats(df: pd.DataFrame) -> dict:
    """Compute descriptive statistics for all numeric columns."""
    result = {}
    num_cols = df.select_dtypes(include="number").columns
    for col in num_cols:
        series = df[col].dropna()
        result[col] = {
            "count": int(series.count()),
            "mean": float(series.mean()) if len(series) > 0 else None,
            "std": float(series.std()) if len(series) > 1 else None,
            "min": float(series.min()) if len(series) > 0 else None,
            "25%": float(series.quantile(0.25)) if len(series) > 0 else None,
            "50%": float(series.median()) if len(series) > 0 else None,
            "75%": float(series.quantile(0.75)) if len(series) > 0 else None,
            "max": float(series.max()) if len(series) > 0 else None,
        }
    return result


def _compute_missing(df: pd.DataFrame) -> dict:
    """Compute missing value percentage per column."""
    n = len(df)
    if n == 0:
        return {}
    missing_counts = df.isnull().sum()
    return {
        col: round(float(count) / n * 100, 2)
        for col, count in missing_counts.items()
        if count > 0
    }


def _compute_outliers(df: pd.DataFrame) -> dict:
    """Detect outlier counts per numeric column using IQR method."""
    result = {}
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if len(series) < 4:
            continue
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count = int(((series < lower) | (series > upper)).sum())
        if count > 0:
            result[col] = count
    return result


def _compute_correlations(df: pd.DataFrame) -> dict:
    """Compute correlation matrix for numeric columns."""
    num_df = df.select_dtypes(include="number")
    if num_df.shape[1] < 2:
        return {}
    corr = num_df.corr()
    return {
        col: {c: round(float(v), 4) for c, v in row.items()}
        for col, row in corr.items()
    }


def _generate_narrative(df: pd.DataFrame) -> str:
    """Call LLM to generate an EDA narrative."""
    cols = df.columns.tolist()
    dtypes = [str(d) for d in df.dtypes]
    sample = df.head(5).to_dict(orient="records")
    n_rows = len(df)
    missing_pct = round(df.isna().sum().sum() / df.size * 100, 2) if df.size > 0 else 0

    prompt = (
        "You are a senior data analyst. Given this dataset summary, write a clear, "
        "concise EDA narrative (3-4 sentences). Focus on: data shape, key patterns, "
        "potential issues, and one actionable recommendation.\n\n"
        f"Columns: {cols}\n"
        f"Dtypes: {dtypes}\n"
        f"Rows: {n_rows}\n"
        f"Missing: {missing_pct}%\n"
        f"Sample: {sample}\n\n"
        "Return plain text only. No markdown, no XML tags."
    )
    try:
        text, _ = get_llm_response(
            prompt, temperature=0.3, max_tokens=300,
            groq_model=GROQ_MODEL_SMALL, module_name="eda"
        )
        return text.strip()
    except Exception:
        return "AI narrative generation failed."


@router.post("/eda")
def run_eda_analysis(req: EDARequest):
    session = get_session(req.session_id)
    if not session or "df" not in session:
        raise HTTPException(status_code=404, detail="Session or DataFrame not found")

    try:
        df = session["df"]
        if isinstance(df, (list, dict)):
            df = pd.DataFrame(df)

        stats = _compute_stats(df)
        missing = _compute_missing(df)
        outliers = _compute_outliers(df)
        correlations = _compute_correlations(df)
        narrative = _generate_narrative(df)

        column_types = {
            "numeric": df.select_dtypes(include="number").columns.tolist(),
            "categorical": df.select_dtypes(include=["object", "category"]).columns.tolist(),
            "datetime": df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist(),
        }

        result_dict = clean_for_json({
            "stats": stats,
            "missing": missing,
            "outliers": outliers,
            "correlations": correlations,
            "narrative": narrative,
            "column_types": column_types,
        })

        update_session(req.session_id, "eda_results", result_dict)

        return result_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
