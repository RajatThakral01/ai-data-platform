"""
ml_engine.py – Automated ML training & comparison for the AI Data Platform.

Automatically detects whether the target column represents a **classification**
or **regression** task, trains multiple models, evaluates them with appropriate
metrics, and returns a structured comparison dictionary.

Supported models:
    • Logistic Regression / Linear Regression
    • Random Forest (Classifier / Regressor)
    • SVM (SVC / SVR)
    • KNN (Classifier / Regressor)
    • XGBoost (Classifier / Regressor)

Usage:
    from modules.ml_engine import run_ml

    results = run_ml(df, target_column="Churn")
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC, SVR

try:
    from xgboost import XGBClassifier, XGBRegressor
    _HAS_XGBOOST = True
except Exception:  # XGBoostError, ImportError, OSError, etc.
    _HAS_XGBOOST = False
    XGBClassifier = None  # type: ignore[assignment,misc]
    XGBRegressor = None   # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_TEST_SIZE: float = 0.2
_RANDOM_STATE: int = 42
_CLASSIFICATION_UNIQUE_THRESHOLD: int = 20  # max unique values to treat as class labels


# ---------------------------------------------------------------------------
# Task-type detection
# ---------------------------------------------------------------------------
def detect_task_type(
    series: pd.Series,
    *,
    threshold: int = _CLASSIFICATION_UNIQUE_THRESHOLD,
) -> str:
    """Infer whether *series* represents a classification or regression target.

    Heuristic:
        • ``object``, ``category``, or ``bool`` dtype → **classification**
        • Numeric with ≤ *threshold* unique (non-null) values → **classification**
        • Otherwise → **regression**

    Returns ``"classification"`` or ``"regression"``.
    """
    if series.dtype.kind in ("O", "b") or isinstance(series.dtype, pd.CategoricalDtype):
        return "classification"
    n_unique = series.dropna().nunique()
    if n_unique <= threshold:
        return "classification"
    return "regression"


# ---------------------------------------------------------------------------
# Preprocessing helper
# ---------------------------------------------------------------------------
def _prepare_data(
    df: pd.DataFrame,
    target_column: str,
    test_size: float,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str, LabelEncoder | None]:
    """Split and preprocess *df* for training.

    Steps:
        1. Separate features (X) and target (y).
        2. Drop rows where target is NaN.
        3. Encode categorical features via one-hot encoding.
        4. Encode categorical target via ``LabelEncoder`` (classification only).
        5. Fill remaining NaN features with column medians.
        6. Train / test split.

    Returns ``(X_train, X_test, y_train, y_test, task_type, label_encoder)``.
    """
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in DataFrame.")

    df = df.dropna(subset=[target_column]).copy()
    if df.empty:
        raise ValueError("No rows remaining after dropping NaN targets.")

    y = df[target_column]
    X = df.drop(columns=[target_column])

    task_type = detect_task_type(y)
    logger.info("Detected task type: %s", task_type)

    # Encode target for classification if needed
    label_enc: LabelEncoder | None = None
    if task_type == "classification" and y.dtype.kind in ("O", "b"):
        label_enc = LabelEncoder()
        y = pd.Series(label_enc.fit_transform(y.astype(str)), index=y.index)

    # One-hot encode categorical features
    cat_cols = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    if cat_cols:
        X = pd.get_dummies(X, columns=cat_cols, drop_first=True)

    # Fill remaining NaN with median (numeric cols only at this point)
    X = X.fillna(X.median(numeric_only=True))
    # If any non-numeric NaN remain, fill with 0
    X = X.fillna(0)

    X_train, X_test, y_train, y_test = train_test_split(
        X.values,
        y.values,
        test_size=test_size,
        random_state=random_state,
        stratify=y.values if task_type == "classification" else None,
    )

    return X_train, X_test, y_train, y_test, task_type, label_enc


# ---------------------------------------------------------------------------
# Model factories
# ---------------------------------------------------------------------------
def _classification_models(random_state: int) -> dict[str, Pipeline]:
    models = {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(
                max_iter=1000, random_state=random_state, n_jobs=-1,
                class_weight="balanced",
            )),
        ]),
        "Random Forest": Pipeline([
            ("model", RandomForestClassifier(
                n_estimators=100, random_state=random_state, n_jobs=-1,
            )),
        ]),
        "SVM": Pipeline([
            ("scaler", StandardScaler()),
            ("model", SVC(
                kernel="rbf", random_state=random_state,
                class_weight="balanced",
            )),
        ]),
        "KNN": Pipeline([
            ("scaler", StandardScaler()),
            ("model", KNeighborsClassifier(n_neighbors=5, n_jobs=-1)),
        ]),
    }
    if _HAS_XGBOOST:
        models["XGBoost"] = Pipeline([
            ("model", XGBClassifier(
                n_estimators=100,
                use_label_encoder=False,
                eval_metric="logloss",
                random_state=random_state,
                verbosity=0,
                n_jobs=-1,
            )),
        ])
    return models


def _regression_models(random_state: int) -> dict[str, Pipeline]:
    models = {
        "Linear Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LinearRegression(n_jobs=-1)),
        ]),
        "Random Forest": Pipeline([
            ("model", RandomForestRegressor(
                n_estimators=100, random_state=random_state, n_jobs=-1,
            )),
        ]),
        "SVR": Pipeline([
            ("scaler", StandardScaler()),
            ("model", SVR(kernel="rbf")),
        ]),
        "KNN": Pipeline([
            ("scaler", StandardScaler()),
            ("model", KNeighborsRegressor(n_neighbors=5, n_jobs=-1)),
        ]),
    }
    if _HAS_XGBOOST:
        models["XGBoost"] = Pipeline([
            ("model", XGBRegressor(
                n_estimators=100,
                random_state=random_state,
                verbosity=0,
                n_jobs=-1,
            )),
        ])
    return models


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------
def _evaluate_classification(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict[str, float]:
    avg = "weighted" if len(np.unique(y_true)) > 2 else "binary"
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, average=avg, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, average=avg, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred, average=avg, zero_division=0)), 4),
    }


def _evaluate_regression(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict[str, float]:
    return {
        "r2_score": round(float(r2_score(y_true, y_pred)), 4),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def run_ml(
    df: pd.DataFrame,
    target_column: str,
    *,
    test_size: float = _TEST_SIZE,
    random_state: int = _RANDOM_STATE,
    models: list[str] | None = None,
) -> dict[str, Any]:
    """Train multiple models on *df* and return a comparison report.

    Parameters
    ----------
    df : pd.DataFrame
        Input data (features + target in a single frame).
    target_column : str
        Name of the column to predict.
    test_size : float
        Fraction of data held out for evaluation (default ``0.2``).
    random_state : int
        Seed for reproducibility (default ``42``).
    models : list[str] | None
        Subset of model names to train. ``None`` → train all five.

    Returns
    -------
    dict[str, Any]
        Keys:
            ``task_type``       – ``"classification"`` or ``"regression"``.
            ``target_column``   – echoed back for convenience.
            ``test_size``       – fraction used.
            ``train_samples``   – number of training rows.
            ``test_samples``    – number of test rows.
            ``class_labels``    – list of label strings (classification only).
            ``results``         – list of dicts, one per model:
                ``{ "model": str, "metrics": dict, "rank": int }``
            ``best_model``      – name of the top-performing model.

    Raises
    ------
    ValueError
        If *target_column* is missing or the DataFrame is invalid.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError(f"Expected a pandas DataFrame, got {type(df).__name__}.")
    if df.empty:
        raise ValueError("Cannot train on an empty DataFrame.")

    # ---- prepare data ------------------------------------------------------
    X_train, X_test, y_train, y_test, task_type, label_enc = _prepare_data(
        df, target_column, test_size, random_state,
    )

    # ---- select models -----------------------------------------------------
    if task_type == "classification":
        all_models = _classification_models(random_state)
        evaluate = _evaluate_classification
        rank_metric = "f1_score"
    else:
        all_models = _regression_models(random_state)
        evaluate = _evaluate_regression
        rank_metric = "r2_score"

    if models is not None:
        unknown = set(models) - set(all_models)
        if unknown:
            raise ValueError(
                f"Unknown model(s): {unknown}. "
                f"Available: {sorted(all_models)}"
            )
        all_models = {k: v for k, v in all_models.items() if k in models}

    # ---- train & evaluate --------------------------------------------------
    results: list[dict[str, Any]] = []
    for name, pipeline in all_models.items():
        logger.info("Training %s …", name)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                pipeline.fit(X_train, y_train)
                y_pred = pipeline.predict(X_test)
                metrics = evaluate(y_test, y_pred)
                results.append({"model": name, "metrics": metrics})
                logger.info("  → %s", metrics)
            except Exception as exc:
                logger.warning("Model '%s' failed: %s", name, exc)
                results.append({
                    "model": name,
                    "metrics": {},
                    "error": str(exc),
                })

    # ---- rank by primary metric -------------------------------------------
    scored = [
        r for r in results
        if rank_metric in r.get("metrics", {})
    ]
    # For regression, higher r2 is better; for classification, higher f1 is better
    scored.sort(key=lambda r: r["metrics"][rank_metric], reverse=True)

    for rank, entry in enumerate(scored, start=1):
        entry["rank"] = rank

    # Mark failed models as unranked
    for r in results:
        if "rank" not in r:
            r["rank"] = None

    best = scored[0]["model"] if scored else None

    # ---- class labels (classification only) --------------------------------
    class_labels: list[str] | None = None
    if label_enc is not None:
        class_labels = label_enc.classes_.tolist()
    elif task_type == "classification":
        class_labels = [str(v) for v in sorted(np.unique(y_test))]

    # ---- assemble output ---------------------------------------------------
    return {
        "task_type": task_type,
        "target_column": target_column,
        "test_size": test_size,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "class_labels": class_labels,
        "results": results,
        "best_model": best,
    }
