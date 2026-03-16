from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from session_store import get_session, update_session
import pandas as pd
import numpy as np
import math

router = APIRouter()


class CleanRequest(BaseModel):
    session_id: str
    auto_clean: bool = True


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


def _auto_clean(df: pd.DataFrame) -> tuple:
    """Run auto-cleaning pipeline. Returns (cleaned_df, changes_log)."""
    cleaned = df.copy()
    changes = []

    # 1. Drop columns with >70% missing
    threshold = 0.7 * len(cleaned)
    cols_to_drop = []
    for col in cleaned.columns:
        miss_count = int(cleaned[col].isna().sum())
        if miss_count > threshold:
            cols_to_drop.append((col, miss_count))
    for col, miss_count in cols_to_drop:
        cleaned = cleaned.drop(columns=[col])
        changes.append({
            "column": col,
            "action": f"Dropped column ({miss_count} missing, >{70}% threshold)",
            "detail": "Column had too many missing values to be useful",
        })

    # 2. Fill numeric NaN with median
    for col in cleaned.select_dtypes(include="number").columns:
        missing_count = int(cleaned[col].isna().sum())
        if missing_count > 0:
            median_val = cleaned[col].median()
            fill_val = float(median_val) if pd.notna(median_val) else 0.0
            cleaned[col] = cleaned[col].fillna(fill_val)
            changes.append({
                "column": col,
                "action": f"Filled {missing_count} missing values with median ({fill_val:.2f})",
                "detail": "Numeric column — median imputation preserves distribution",
            })

    # 3. Fill categorical NaN with mode
    for col in cleaned.select_dtypes(include=["object", "category"]).columns:
        missing_count = int(cleaned[col].isna().sum())
        if missing_count > 0:
            mode_val = cleaned[col].mode()
            fill_val = mode_val.iloc[0] if not mode_val.empty else "Unknown"
            cleaned[col] = cleaned[col].fillna(fill_val)
            changes.append({
                "column": col,
                "action": f"Filled {missing_count} missing values with mode ('{fill_val}')",
                "detail": "Categorical column — mode imputation",
            })

    # 4. Remove duplicate rows
    dup_count = int(cleaned.duplicated().sum())
    if dup_count > 0:
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
        changes.append({
            "column": "*",
            "action": f"Removed {dup_count} duplicate rows",
            "detail": "Exact row duplicates dropped",
        })

    # 5. Cap outliers at IQR 1.5x bounds
    for col in cleaned.select_dtypes(include="number").columns:
        series = cleaned[col].dropna()
        if len(series) < 4:
            continue
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_count = int(((cleaned[col] < lower) | (cleaned[col] > upper)).sum())
        if outlier_count > 0:
            cleaned[col] = cleaned[col].clip(lower=lower, upper=upper)
            changes.append({
                "column": col,
                "action": f"Capped {outlier_count} outliers to IQR bounds [{lower:.2f}, {upper:.2f}]",
                "detail": "IQR 1.5x method — values clipped, not removed",
            })

    return cleaned, changes


@router.post("/clean")
def run_cleaning(req: CleanRequest):
    session = get_session(req.session_id)
    if not session or "df" not in session:
        raise HTTPException(status_code=404, detail="Session or DataFrame not found")

    try:
        df = session["df"]

        before = {
            "rows": len(df),
            "missing_count": int(df.isnull().sum().sum()),
        }

        cleaned_df, changes_log = _auto_clean(df)

        cleaned_df_data = cleaned_df.to_dict(orient="records")

        # Store cleaned data and results back to session
        update_session(req.session_id, "cleaned_df", cleaned_df_data)

        after = {
            "rows": len(cleaned_df),
            "missing_count": int(cleaned_df.isnull().sum().sum()),
        }

        result_dict = clean_for_json({
            "changes_log": changes_log,
            "before": before,
            "after": after,
            "download_url": f"/api/download/{req.session_id}/cleaned",
        })

        update_session(req.session_id, "cleaning_results", result_dict)

        return result_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{session_id}/cleaned")
def download_cleaned(session_id: str):
    session = get_session(session_id)
    if not session or "cleaned_df" not in session:
        raise HTTPException(status_code=404, detail="Cleaned data not found")

    cleaned_df_data = session["cleaned_df"]
    if isinstance(cleaned_df_data, list) or isinstance(cleaned_df_data, dict):
        cleaned_df = pd.DataFrame(cleaned_df_data)
    else:
        cleaned_df = cleaned_df_data

    csv_str = cleaned_df.to_csv(index=False)

    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=cleaned_{session.get('filename', 'data')}.csv"
        },
    )
