from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from session_store import get_session, update_session
import pandas as pd
import numpy as np
import math
import time
import sys
import os

from llm.client_factory import get_llm_response, GROQ_MODEL_SMALL

router = APIRouter()


class MLRequest(BaseModel):
    session_id: str
    target_column: str
    test_size: float = 0.2


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
    if isinstance(obj, np.ndarray):
        return [clean_for_json(x) for x in obj.tolist()]
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(i) for i in obj]
    return obj


def _detect_task_type(series: pd.Series) -> str:
    """Classify vs regression based on unique value count."""
    nunique = series.nunique()
    if nunique <= 20:
        return "classification"
    return "regression"


def _prepare_features(df: pd.DataFrame, target_col: str):
    """Prepare X and y from DataFrame. Encodes categoricals, drops NaN."""
    from sklearn.preprocessing import LabelEncoder

    work = df.copy()

    # Separate target
    y = work[target_col].copy()
    X = work.drop(columns=[target_col])

    # Drop non-numeric, non-categorical columns that can't be encoded
    # Keep only numeric and object/category columns
    usable = X.select_dtypes(include=["number", "object", "category"]).columns
    X = X[usable]

    # Label encode categoricals
    encoders = {}
    for col in X.select_dtypes(include=["object", "category"]).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        encoders[col] = le

    # Encode target if categorical
    target_encoder = None
    if y.dtype == "object" or y.dtype.name == "category":
        target_encoder = LabelEncoder()
        y = pd.Series(target_encoder.fit_transform(y.astype(str)))

    # Drop rows with NaN
    combined = pd.concat([X, y.rename("__target__")], axis=1).dropna()
    X = combined.drop(columns=["__target__"])
    y = combined["__target__"]

    return X, y, target_encoder


@router.post("/ml")
def run_ml(req: MLRequest):
    session = get_session(req.session_id)
    if not session or "df" not in session:
        raise HTTPException(status_code=404, detail="Session or DataFrame not found")

    df = session.get("cleaned_df", session["df"])
    
    # Handle serialized data (list/dict) by reconstructing DataFrame
    if isinstance(df, (list, dict)):
        df = pd.DataFrame(df)

    if req.target_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{req.target_column}' not in dataset")

    try:
        from sklearn.model_selection import train_test_split
        from sklearn.linear_model import LogisticRegression, LinearRegression
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, f1_score,
            r2_score, mean_squared_error,
        )

        task_type = _detect_task_type(df[req.target_column])
        X, y, _ = _prepare_features(df, req.target_column)

        if len(X) < 10:
            raise HTTPException(status_code=400, detail="Not enough data rows after cleaning")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=req.test_size, random_state=42
        )

        if task_type == "classification":
            models_to_run = [
                ("Logistic Regression", LogisticRegression(max_iter=1000, random_state=42)),
                ("Random Forest", RandomForestClassifier(n_estimators=100, random_state=42)),
                ("Gradient Boosting", GradientBoostingClassifier(n_estimators=100, random_state=42)),
            ]
        else:
            models_to_run = [
                ("Linear Regression", LinearRegression()),
                ("Random Forest", RandomForestRegressor(n_estimators=100, random_state=42)),
                ("Gradient Boosting", GradientBoostingRegressor(n_estimators=100, random_state=42)),
            ]

        results = []
        best_score = -float("inf")
        best_name = ""

        for name, model in models_to_run:
            start = time.time()
            model.fit(X_train, y_train)
            elapsed_ms = int((time.time() - start) * 1000)
            y_pred = model.predict(X_test)

            if task_type == "classification":
                acc = float(accuracy_score(y_test, y_pred))
                prec = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
                rec = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
                f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
                score = acc
                results.append({
                    "name": name,
                    "accuracy": round(acc, 4),
                    "precision": round(prec, 4),
                    "recall": round(rec, 4),
                    "f1": round(f1, 4),
                    "score": round(acc, 4),
                    "training_time_ms": elapsed_ms,
                })
            else:
                r2 = float(r2_score(y_test, y_pred))
                rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
                score = r2
                results.append({
                    "name": name,
                    "r2": round(r2, 4),
                    "rmse": round(rmse, 4),
                    "score": round(r2, 4),
                    "training_time_ms": elapsed_ms,
                })

            if score > best_score:
                best_score = score
                best_name = name

        # Generate AI summary
        metric_label = "accuracy" if task_type == "classification" else "R²"
        summary_prompt = (
            f"You are a machine learning expert. A {task_type} task was run "
            f"on a dataset with {len(df)} rows, target column '{req.target_column}'.\n"
            f"Results:\n"
        )
        for r in results:
            summary_prompt += f"- {r['name']}: {metric_label}={r['score']:.4f}, time={r['training_time_ms']}ms\n"
        summary_prompt += (
            f"\nBest model: {best_name}\n"
            "Write a 2-3 sentence summary for a non-technical stakeholder. "
            "Include the best model name, its score, and a recommendation. "
            "Plain text only, no markdown."
        )
        try:
            ai_summary, _ = get_llm_response(
                summary_prompt, temperature=0.3, max_tokens=300,
                groq_model=GROQ_MODEL_SMALL, module_name="ml"
            )
        except Exception:
            ai_summary = f"Best model: {best_name} with {metric_label} of {best_score:.4f}."

        # Check for data leakage
        leakage_warnings = []
        num_cols = df.select_dtypes(include="number").columns
        if req.target_column in num_cols:
            for col in num_cols:
                if col == req.target_column:
                    continue
                try:
                    corr_val = abs(float(df[col].corr(df[req.target_column])))
                    if corr_val > 0.95:
                        leakage_warnings.append(
                            f"Potential leakage: '{col}' has {corr_val:.2f} correlation with target"
                        )
                except Exception:
                    pass

        result_dict = clean_for_json({
            "task_type": task_type,
            "models": results,
            "best_model": best_name,
            "ai_summary": ai_summary.strip(),
            "leakage_warnings": leakage_warnings,
        })

        update_session(req.session_id, "ml_results", result_dict)

        return result_dict

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
