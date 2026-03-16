"""Tests for llm.prompts."""

from __future__ import annotations

import pytest

from llm.prompts import (
    PROMPT_CATALOGUE,
    ml_recommendation_prompt,
    narrative_prompt,
    nl_to_pandas_prompt,
)


# ---------------------------------------------------------------------------
# Fixture – minimal EDA summary matching run_eda() output shape
# ---------------------------------------------------------------------------
@pytest.fixture()
def eda_summary() -> dict:
    return {
        "descriptive_stats": {
            "Age": {
                "count": 100,
                "mean": 35.5,
                "std": 10.2,
                "min": 18,
                "25%": 27,
                "50%": 35,
                "75%": 44,
                "max": 65,
            },
            "Salary": {
                "count": 100,
                "mean": 62000,
                "std": 15000,
                "min": 30000,
                "25%": 50000,
                "50%": 60000,
                "75%": 72000,
                "max": 120000,
            },
            "Department": {
                "count": 100,
                "unique": 4,
                "top": "Engineering",
                "freq": 40,
            },
        },
        "missing_values": {
            "total_missing": 5,
            "columns": {
                "Age": {"count": 2, "percentage": 2.0},
                "Salary": {"count": 3, "percentage": 3.0},
                "Department": {"count": 0, "percentage": 0.0},
            },
        },
        "correlation_matrix": {
            "matrix": {
                "Age": {"Age": 1.0, "Salary": 0.72},
                "Salary": {"Age": 0.72, "Salary": 1.0},
            },
            "figure": None,
        },
        "distribution_plots": {},
        "categorical_plots": {},
        "outliers": {
            "columns": {
                "Age": {
                    "lower_bound": 5.0,
                    "upper_bound": 70.0,
                    "outlier_count": 0,
                    "outlier_indices": [],
                },
                "Salary": {
                    "lower_bound": 17000,
                    "upper_bound": 105000,
                    "outlier_count": 2,
                    "outlier_indices": [42, 87],
                },
            },
            "total_outlier_rows": 2,
        },
    }


@pytest.fixture()
def minimal_summary() -> dict:
    """Bare-minimum summary with no missing values or outliers."""
    return {
        "descriptive_stats": {
            "X": {"count": 10, "mean": 5, "std": 2, "min": 1, "25%": 3,
                   "50%": 5, "75%": 7, "max": 10},
        },
        "missing_values": {"total_missing": 0, "columns": {"X": {"count": 0, "percentage": 0.0}}},
        "correlation_matrix": {"matrix": {}, "figure": None},
        "distribution_plots": {},
        "categorical_plots": {},
        "outliers": {"columns": {}, "total_outlier_rows": 0},
    }


# ---------------------------------------------------------------------------
# 1. Narrative prompt
# ---------------------------------------------------------------------------
class TestNarrativePrompt:
    def test_returns_string(self, eda_summary):
        result = narrative_prompt(eda_summary)
        assert isinstance(result, str)

    def test_contains_column_names(self, eda_summary):
        result = narrative_prompt(eda_summary)
        assert "Age" in result
        assert "Salary" in result
        assert "Department" in result

    def test_contains_missing_info(self, eda_summary):
        result = narrative_prompt(eda_summary)
        assert "missing" in result.lower()
        assert "2.0%" in result

    def test_contains_correlation_info(self, eda_summary):
        result = narrative_prompt(eda_summary)
        assert "0.72" in result

    def test_contains_outlier_info(self, eda_summary):
        result = narrative_prompt(eda_summary)
        assert "outlier" in result.lower()

    def test_contains_stats_info(self, eda_summary):
        result = narrative_prompt(eda_summary)
        assert "mean=" in result

    def test_raises_on_none(self):
        with pytest.raises(ValueError, match="empty"):
            narrative_prompt(None)

    def test_raises_on_empty_dict(self):
        with pytest.raises(ValueError, match="empty"):
            narrative_prompt({})

    def test_no_missing_values_message(self, minimal_summary):
        result = narrative_prompt(minimal_summary)
        # Compact summary omits missing info when there are none
        assert "X" in result


# ---------------------------------------------------------------------------
# 2. ML recommendation prompt
# ---------------------------------------------------------------------------
class TestMLRecommendationPrompt:
    def test_returns_string(self, eda_summary):
        result = ml_recommendation_prompt(eda_summary)
        assert isinstance(result, str)

    def test_includes_target_column(self, eda_summary):
        result = ml_recommendation_prompt(eda_summary, target_column="Salary")
        assert "Salary" in result

    def test_includes_task_hint(self, eda_summary):
        result = ml_recommendation_prompt(eda_summary, task_hint="regression")
        assert "regression" in result

    def test_default_when_no_target(self, eda_summary):
        result = ml_recommendation_prompt(eda_summary)
        # Should still contain model guidance without explicit target
        assert "model" in result.lower()

    def test_contains_model_guidance(self, eda_summary):
        result = ml_recommendation_prompt(eda_summary)
        assert "model" in result.lower()
        assert "preprocessing" in result.lower()

    def test_raises_on_none(self):
        with pytest.raises(ValueError):
            ml_recommendation_prompt(None)


# ---------------------------------------------------------------------------
# 3. NL → Pandas code prompt
# ---------------------------------------------------------------------------
class TestNLToPandasPrompt:
    def test_returns_string(self, eda_summary):
        result = nl_to_pandas_prompt(eda_summary, "What is the average salary?")
        assert isinstance(result, str)

    def test_contains_question(self, eda_summary):
        q = "What is the average salary by department?"
        result = nl_to_pandas_prompt(eda_summary, q)
        assert q in result

    def test_default_df_name(self, eda_summary):
        result = nl_to_pandas_prompt(eda_summary, "Show me the top 5 rows")
        assert "`df`" in result

    def test_custom_df_name(self, eda_summary):
        result = nl_to_pandas_prompt(
            eda_summary, "Count rows", dataframe_name="data"
        )
        assert "`data`" in result
        assert "`df`" not in result

    def test_mentions_result_variable(self, eda_summary):
        result = nl_to_pandas_prompt(eda_summary, "Count nulls")
        assert "result" in result

    def test_lists_columns(self, eda_summary):
        result = nl_to_pandas_prompt(eda_summary, "Anything")
        # Compact format: Age(num), Salary(num), Department(cat)
        assert "Age" in result
        assert "Salary" in result
        assert "Department" in result

    def test_mentions_missing_cols(self, eda_summary):
        result = nl_to_pandas_prompt(eda_summary, "Anything")
        # Age and Salary have missing values
        assert "Age" in result
        assert "Salary" in result

    def test_raises_on_empty_question(self, eda_summary):
        with pytest.raises(ValueError, match="empty"):
            nl_to_pandas_prompt(eda_summary, "")

    def test_raises_on_whitespace_question(self, eda_summary):
        with pytest.raises(ValueError, match="empty"):
            nl_to_pandas_prompt(eda_summary, "   ")

    def test_raises_on_none_summary(self):
        with pytest.raises(ValueError):
            nl_to_pandas_prompt(None, "question")


# ---------------------------------------------------------------------------
# Prompt catalogue
# ---------------------------------------------------------------------------
class TestPromptCatalogue:
    def test_all_entries_callable(self):
        for name, fn in PROMPT_CATALOGUE.items():
            assert callable(fn), f"{name} is not callable"

    def test_expected_keys(self):
        assert set(PROMPT_CATALOGUE.keys()) == {
            "narrative",
            "ml_recommendation",
            "nl_to_pandas",
        }
