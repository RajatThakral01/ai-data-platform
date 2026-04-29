"""Tests for modules.eda."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from modules.eda import run_eda


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Mixed numeric + categorical DataFrame with a known duplicate and NaNs."""
    np.random.seed(42)
    return pd.DataFrame(
        {
            "Age": [25, 30, 35, 40, 45, 50, 200, 30, None, 28],
            "Salary": [
                40000,
                50000,
                60000,
                70000,
                80000,
                90000,
                100000,
                50000,
                55000,
                None,
            ],
            "Department": [
                "HR",
                "IT",
                "IT",
                "Finance",
                "HR",
                "IT",
                "Finance",
                "IT",
                "HR",
                "Finance",
            ],
            "Status": [
                "Active",
                "Active",
                "Inactive",
                "Active",
                "Inactive",
                "Active",
                "Active",
                "Active",
                None,
                "Active",
            ],
        }
    )


@pytest.fixture()
def numeric_only_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "A": [1, 2, 3, 4, 5, 100],
            "B": [10, 20, 30, 40, 50, 60],
        }
    )


@pytest.fixture()
def categorical_only_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Color": ["Red", "Blue", "Green", "Red", "Blue"],
            "Size": ["S", "M", "L", "M", "S"],
        }
    )


# ---------------------------------------------------------------------------
# Structural / smoke tests
# ---------------------------------------------------------------------------
class TestRunEDAStructure:
    def test_returns_dict(self, sample_df: pd.DataFrame):
        results = run_eda(sample_df)
        assert isinstance(results, dict)

    def test_all_keys_present(self, sample_df: pd.DataFrame):
        results = run_eda(sample_df)
        expected_keys = {
            "descriptive_stats",
            "missing_values",
            "correlation_matrix",
            "distribution_plots",
            "categorical_plots",
            "outliers",
        }
        assert results.keys() == expected_keys

    def test_rejects_none(self):
        with pytest.raises(ValueError):
            run_eda(None)

    def test_rejects_non_dataframe(self):
        with pytest.raises(ValueError):
            run_eda({"a": [1, 2, 3]})

    def test_rejects_empty_df(self):
        with pytest.raises(ValueError):
            run_eda(pd.DataFrame())


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------
class TestDescriptiveStats:
    def test_numeric_stats(self, sample_df: pd.DataFrame):
        stats = run_eda(sample_df)["descriptive_stats"]
        assert "Age" in stats
        assert "mean" in stats["Age"]
        assert "std" in stats["Age"]

    def test_categorical_stats(self, sample_df: pd.DataFrame):
        stats = run_eda(sample_df)["descriptive_stats"]
        assert "Department" in stats
        assert "unique" in stats["Department"]
        assert "top" in stats["Department"]

    def test_values_are_python_native(self, numeric_only_df: pd.DataFrame):
        stats = run_eda(numeric_only_df)["descriptive_stats"]
        for col_stats in stats.values():
            for v in col_stats.values():
                assert not isinstance(v, (np.generic,)), f"Non-native type: {type(v)}"


# ---------------------------------------------------------------------------
# Missing-value analysis
# ---------------------------------------------------------------------------
class TestMissingValues:
    def test_total_missing(self, sample_df: pd.DataFrame):
        mv = run_eda(sample_df)["missing_values"]
        assert mv["total_missing"] >= 1

    def test_per_column_count(self, sample_df: pd.DataFrame):
        mv = run_eda(sample_df)["missing_values"]
        assert mv["columns"]["Age"]["count"] == 1
        assert mv["columns"]["Salary"]["count"] == 1

    def test_percentages(self, sample_df: pd.DataFrame):
        mv = run_eda(sample_df)["missing_values"]
        # 1 missing out of 10 rows → 10.0 %
        assert mv["columns"]["Age"]["percentage"] == 10.0


# ---------------------------------------------------------------------------
# Correlation matrix
# ---------------------------------------------------------------------------
class TestCorrelationMatrix:
    def test_matrix_dict(self, sample_df: pd.DataFrame):
        cm = run_eda(sample_df)["correlation_matrix"]
        assert "Age" in cm["matrix"]
        assert "Salary" in cm["matrix"]["Age"]

    def test_self_correlation_is_one(self, numeric_only_df: pd.DataFrame):
        cm = run_eda(numeric_only_df)["correlation_matrix"]
        assert cm["matrix"]["A"]["A"] == pytest.approx(1.0)

    def test_figure_is_plotly(self, sample_df: pd.DataFrame):
        cm = run_eda(sample_df)["correlation_matrix"]
        assert isinstance(cm["figure"], go.Figure)

    def test_skipped_with_single_numeric(self, categorical_only_df: pd.DataFrame):
        cm = run_eda(categorical_only_df)["correlation_matrix"]
        assert cm["matrix"] == {}
        assert cm["figure"] is None


# ---------------------------------------------------------------------------
# Distribution plots
# ---------------------------------------------------------------------------
class TestDistributionPlots:
    def test_one_per_numeric_col(self, sample_df: pd.DataFrame):
        plots = run_eda(sample_df)["distribution_plots"]
        assert "Age" in plots
        assert "Salary" in plots
        assert "Department" not in plots

    def test_figures_are_plotly(self, sample_df: pd.DataFrame):
        for fig in run_eda(sample_df)["distribution_plots"].values():
            assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Categorical plots
# ---------------------------------------------------------------------------
class TestCategoricalPlots:
    def test_one_per_cat_col(self, sample_df: pd.DataFrame):
        plots = run_eda(sample_df)["categorical_plots"]
        assert "Department" in plots
        assert "Status" in plots
        assert "Age" not in plots

    def test_high_cardinality_skipped(self):
        df = pd.DataFrame({"ID": [f"id_{i}" for i in range(50)]})
        plots = run_eda(df, max_categories=30)["categorical_plots"]
        assert "ID" not in plots

    def test_figures_are_plotly(self, sample_df: pd.DataFrame):
        for fig in run_eda(sample_df)["categorical_plots"].values():
            assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Outlier detection (IQR)
# ---------------------------------------------------------------------------
class TestOutlierDetection:
    def test_structure(self, sample_df: pd.DataFrame):
        outliers = run_eda(sample_df)["outliers"]
        assert "columns" in outliers
        assert "total_outlier_rows" in outliers

    def test_detects_known_outlier(self, sample_df: pd.DataFrame):
        """Age=200 is an extreme outlier for the sample data."""
        outliers = run_eda(sample_df)["outliers"]
        age_info = outliers["columns"]["Age"]
        assert age_info["outlier_count"] >= 1
        # Row index 6 has Age=200
        assert 6 in age_info["outlier_indices"]

    def test_bounds_present(self, numeric_only_df: pd.DataFrame):
        outliers = run_eda(numeric_only_df)["outliers"]
        for col_info in outliers["columns"].values():
            assert "lower_bound" in col_info
            assert "upper_bound" in col_info

    def test_custom_iqr_multiplier(self, numeric_only_df: pd.DataFrame):
        # With a very large multiplier, nothing should be an outlier
        outliers = run_eda(numeric_only_df, iqr_multiplier=100.0)["outliers"]
        for col_info in outliers["columns"].values():
            assert col_info["outlier_count"] == 0

    def test_total_outlier_rows(self, sample_df: pd.DataFrame):
        outliers = run_eda(sample_df)["outliers"]
        assert outliers["total_outlier_rows"] >= 1
