"""Tests for modules.ml_engine."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from modules.ml_engine import _HAS_XGBOOST, detect_task_type, run_ml

_EXPECTED_MODEL_COUNT = 5 if _HAS_XGBOOST else 4


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def classification_df() -> pd.DataFrame:
    """Binary classification dataset (100 rows)."""
    np.random.seed(42)
    n = 100
    return pd.DataFrame(
        {
            "Feature1": np.random.randn(n),
            "Feature2": np.random.randn(n),
            "Feature3": np.random.choice(["A", "B", "C"], size=n),
            "Target": np.random.choice(["Yes", "No"], size=n),
        }
    )


@pytest.fixture()
def regression_df() -> pd.DataFrame:
    """Continuous regression dataset (120 rows)."""
    np.random.seed(42)
    n = 120
    x1 = np.random.randn(n)
    x2 = np.random.randn(n)
    y = 3 * x1 + 2 * x2 + np.random.randn(n) * 0.5
    return pd.DataFrame({"X1": x1, "X2": x2, "Target": y})


@pytest.fixture()
def multiclass_df() -> pd.DataFrame:
    """3-class classification dataset (150 rows)."""
    np.random.seed(42)
    n = 150
    return pd.DataFrame(
        {
            "A": np.random.randn(n),
            "B": np.random.randn(n),
            "Label": np.random.choice(["cat", "dog", "bird"], size=n),
        }
    )


@pytest.fixture()
def df_with_missing(classification_df: pd.DataFrame) -> pd.DataFrame:
    """Classification data with some NaN features and a NaN target row."""
    df = classification_df.copy()
    df.loc[0, "Feature1"] = np.nan
    df.loc[5, "Feature2"] = np.nan
    df.loc[10, "Target"] = np.nan
    return df


# ---------------------------------------------------------------------------
# Task-type detection
# ---------------------------------------------------------------------------
class TestDetectTaskType:
    def test_object_dtype_is_classification(self):
        s = pd.Series(["a", "b", "c", "a"])
        assert detect_task_type(s) == "classification"

    def test_bool_dtype_is_classification(self):
        s = pd.Series([True, False, True, False])
        assert detect_task_type(s) == "classification"

    def test_low_cardinality_int_is_classification(self):
        s = pd.Series([0, 1, 0, 1, 0, 1])
        assert detect_task_type(s) == "classification"

    def test_continuous_float_is_regression(self):
        s = pd.Series(np.random.randn(100))
        assert detect_task_type(s) == "regression"

    def test_high_cardinality_int_is_regression(self):
        s = pd.Series(range(50))
        assert detect_task_type(s) == "regression"

    def test_custom_threshold(self):
        s = pd.Series(range(10))
        assert detect_task_type(s, threshold=5) == "regression"
        assert detect_task_type(s, threshold=15) == "classification"


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
class TestClassification:
    def test_returns_dict(self, classification_df: pd.DataFrame):
        result = run_ml(classification_df, "Target")
        assert isinstance(result, dict)

    def test_task_type_detected(self, classification_df: pd.DataFrame):
        result = run_ml(classification_df, "Target")
        assert result["task_type"] == "classification"

    def test_all_expected_keys(self, classification_df: pd.DataFrame):
        result = run_ml(classification_df, "Target")
        expected = {
            "task_type", "target_column", "test_size",
            "train_samples", "test_samples", "class_labels",
            "results", "best_model", "skipped_models",
            "leakage_warnings",
        }
        assert result.keys() == expected

    def test_all_models_trained(self, classification_df: pd.DataFrame):
        result = run_ml(classification_df, "Target")
        assert len(result["results"]) == _EXPECTED_MODEL_COUNT

    def test_classification_metrics(self, classification_df: pd.DataFrame):
        result = run_ml(classification_df, "Target")
        for entry in result["results"]:
            if entry["metrics"]:  # skip failed models
                assert "accuracy" in entry["metrics"]
                assert "f1_score" in entry["metrics"]
                assert "precision" in entry["metrics"]
                assert "recall" in entry["metrics"]

    def test_best_model_present(self, classification_df: pd.DataFrame):
        result = run_ml(classification_df, "Target")
        assert result["best_model"] is not None

    def test_ranked(self, classification_df: pd.DataFrame):
        result = run_ml(classification_df, "Target")
        ranks = [r["rank"] for r in result["results"] if r["rank"] is not None]
        assert sorted(ranks) == list(range(1, len(ranks) + 1))

    def test_class_labels(self, classification_df: pd.DataFrame):
        result = run_ml(classification_df, "Target")
        assert set(result["class_labels"]) == {"No", "Yes"}


# ---------------------------------------------------------------------------
# Multiclass
# ---------------------------------------------------------------------------
class TestMulticlass:
    def test_multiclass_detected(self, multiclass_df: pd.DataFrame):
        result = run_ml(multiclass_df, "Label")
        assert result["task_type"] == "classification"

    def test_three_labels(self, multiclass_df: pd.DataFrame):
        result = run_ml(multiclass_df, "Label")
        assert len(result["class_labels"]) == 3


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------
class TestRegression:
    def test_task_type_detected(self, regression_df: pd.DataFrame):
        result = run_ml(regression_df, "Target")
        assert result["task_type"] == "regression"

    def test_regression_metrics(self, regression_df: pd.DataFrame):
        result = run_ml(regression_df, "Target")
        for entry in result["results"]:
            if entry["metrics"]:
                assert "r2_score" in entry["metrics"]
                assert "mae" in entry["metrics"]
                assert "rmse" in entry["metrics"]

    def test_no_class_labels(self, regression_df: pd.DataFrame):
        result = run_ml(regression_df, "Target")
        assert result["class_labels"] is None

    def test_best_model_present(self, regression_df: pd.DataFrame):
        result = run_ml(regression_df, "Target")
        assert result["best_model"] is not None


# ---------------------------------------------------------------------------
# Model subset selection
# ---------------------------------------------------------------------------
class TestModelSubset:
    def test_train_only_selected(self, regression_df: pd.DataFrame):
        selected = ["Random Forest", "KNN"]
        result = run_ml(regression_df, "Target", models=selected)
        names = {r["model"] for r in result["results"]}
        assert names == set(selected)

    def test_unknown_model_raises(self, regression_df: pd.DataFrame):
        with pytest.raises(ValueError, match="Unknown"):
            run_ml(regression_df, "Target", models=["FakeModel"])


# ---------------------------------------------------------------------------
# Missing data handling
# ---------------------------------------------------------------------------
class TestMissingData:
    def test_handles_nan_features(self, df_with_missing: pd.DataFrame):
        result = run_ml(df_with_missing, "Target")
        assert result["best_model"] is not None

    def test_drops_nan_target_rows(self, df_with_missing: pd.DataFrame):
        result = run_ml(df_with_missing, "Target")
        # Original had 100 rows, 1 NaN target → 99 usable
        assert result["train_samples"] + result["test_samples"] == 99


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------
class TestValidationErrors:
    def test_none_input(self):
        with pytest.raises(ValueError, match="DataFrame"):
            run_ml(None, "Target")

    def test_empty_df(self):
        with pytest.raises(ValueError, match="empty"):
            run_ml(pd.DataFrame(), "Target")

    def test_missing_target_column(self, classification_df: pd.DataFrame):
        with pytest.raises(ValueError, match="not found"):
            run_ml(classification_df, "NonExistent")
