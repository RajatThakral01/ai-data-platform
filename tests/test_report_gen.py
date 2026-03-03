"""Tests for modules.report_gen."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from modules.report_gen import (
    _build_conclusion_prompt,
    _build_insights_prompt,
    _fmt,
    _render_correlation_heatmap,
    _render_distribution_chart,
    _title_case,
    generate_report,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def full_report_data() -> dict:
    """Comprehensive report input dict matching the outputs of all modules."""
    return {
        "title": "Quarterly Sales Analysis",
        "author": "AI Data Platform",
        "date": "2026-02-25",
        "description": "Automated analysis of Q4 sales data across all regions.",
        "dataset_overview": {
            "filename": "sales_q4.csv",
            "rows": 5000,
            "columns": 12,
            "file_size": "2.3 MB",
            "column_names": [
                "OrderID", "Date", "Region", "Product",
                "Quantity", "Revenue", "Profit",
            ],
            "dtypes": {
                "OrderID": "int64",
                "Date": "datetime64",
                "Region": "object",
                "Product": "object",
                "Quantity": "int64",
                "Revenue": "float64",
                "Profit": "float64",
            },
        },
        "eda_summary": {
            "descriptive_stats": {
                "Quantity": {
                    "count": 5000, "mean": 25.3, "std": 12.1,
                    "min": 1, "max": 100,
                },
                "Revenue": {
                    "count": 5000, "mean": 4500.50, "std": 2100.0,
                    "min": 50.0, "max": 25000.0,
                },
                "Region": {
                    "count": 5000, "unique": 4, "top": "West", "freq": 1500,
                },
            },
            "missing_values": {
                "total_missing": 23,
                "columns": {
                    "Quantity": {"count": 0, "percentage": 0.0},
                    "Revenue": {"count": 15, "percentage": 0.3},
                    "Profit": {"count": 8, "percentage": 0.16},
                    "Region": {"count": 0, "percentage": 0.0},
                },
            },
            "outliers": {
                "total_outlier_rows": 42,
                "columns": {
                    "Revenue": {
                        "outlier_count": 30,
                        "lower_bound": -500.0,
                        "upper_bound": 15000.0,
                    },
                    "Quantity": {
                        "outlier_count": 12,
                        "lower_bound": 0,
                        "upper_bound": 60,
                    },
                },
            },
            "correlation_matrix": {
                "matrix": {
                    "Quantity": {"Quantity": 1.0, "Revenue": 0.82},
                    "Revenue": {"Quantity": 0.82, "Revenue": 1.0},
                },
            },
            "key_findings": [
                "Revenue is right-skewed with a long tail.",
                "West region has the highest sales volume.",
                "Strong correlation (r=0.82) between Quantity and Revenue.",
            ],
        },
        "ml_comparison": {
            "task_type": "regression",
            "target_column": "Revenue",
            "train_samples": 4000,
            "test_samples": 1000,
            "best_model": "Random Forest",
            "results": [
                {
                    "model": "Random Forest",
                    "rank": 1,
                    "metrics": {"r2_score": 0.9234, "mae": 320.5, "rmse": 450.2},
                },
                {
                    "model": "XGBoost",
                    "rank": 2,
                    "metrics": {"r2_score": 0.9101, "mae": 345.8, "rmse": 478.1},
                },
                {
                    "model": "Linear Regression",
                    "rank": 3,
                    "metrics": {"r2_score": 0.7845, "mae": 580.3, "rmse": 720.6},
                },
            ],
        },
        "ai_summary": (
            "The Q4 sales dataset reveals strong performance across all regions, "
            "with the West region leading in both volume and revenue.\n\n"
            "Revenue distribution is right-skewed, indicating a few high-value "
            "transactions that could be worth investigating."
        ),
        # Pre-provide AI sections to avoid needing a live Ollama server
        "ai_insights": (
            "The dataset contains 5,000 records with an average revenue of "
            "$4,500 per transaction. Revenue shows high variability (std=$2,100) "
            "and a right-skewed distribution. There are 23 missing values, "
            "mostly in Revenue and Profit columns."
        ),
        "conclusion": (
            "The analysis reveals a healthy sales pipeline with strong "
            "correlation between quantity and revenue. The Random Forest "
            "model achieved the best predictive accuracy.\n\n"
            "Recommended next steps: investigate the 42 outlier rows for "
            "data quality issues, address missing values in Revenue/Profit, "
            "and deploy the Random Forest model for revenue forecasting."
        ),
    }


@pytest.fixture()
def minimal_report_data() -> dict:
    return {"title": "Minimal Report"}


@pytest.fixture()
def output_pdf(tmp_path: Path) -> Path:
    return tmp_path / "test_report.pdf"


# ---------------------------------------------------------------------------
# Tests – Report generation
# ---------------------------------------------------------------------------
class TestGenerateReport:
    def test_creates_pdf(self, full_report_data, output_pdf):
        path = generate_report(full_report_data, output_pdf)
        assert Path(path).exists()
        assert path.endswith(".pdf")

    def test_pdf_not_empty(self, full_report_data, output_pdf):
        generate_report(full_report_data, output_pdf)
        assert output_pdf.stat().st_size > 0

    def test_pdf_header(self, full_report_data, output_pdf):
        generate_report(full_report_data, output_pdf)
        with open(output_pdf, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_returns_absolute_path(self, full_report_data, output_pdf):
        path = generate_report(full_report_data, output_pdf)
        assert os.path.isabs(path)

    def test_creates_parent_dirs(self, full_report_data, tmp_path):
        nested = tmp_path / "deep" / "nested" / "report.pdf"
        path = generate_report(full_report_data, nested)
        assert Path(path).exists()

    def test_minimal_data(self, minimal_report_data, output_pdf):
        path = generate_report(minimal_report_data, output_pdf)
        assert Path(path).exists()
        assert output_pdf.stat().st_size > 0

    def test_only_eda(self, output_pdf):
        data = {
            "title": "EDA Only",
            "ai_insights": "Test insight.",
            "eda_summary": {
                "descriptive_stats": {
                    "X": {"count": 10, "mean": 5.0, "std": 2.0, "min": 1, "max": 10}
                },
                "missing_values": {
                    "total_missing": 0,
                    "columns": {"X": {"count": 0, "percentage": 0.0}},
                },
            },
        }
        path = generate_report(data, output_pdf)
        assert Path(path).exists()

    def test_only_ml(self, output_pdf):
        data = {
            "title": "ML Only",
            "ml_comparison": {
                "task_type": "classification",
                "target_column": "Label",
                "train_samples": 80,
                "test_samples": 20,
                "best_model": "SVM",
                "results": [
                    {
                        "model": "SVM",
                        "rank": 1,
                        "metrics": {"accuracy": 0.95, "f1_score": 0.94},
                    }
                ],
            },
        }
        path = generate_report(data, output_pdf)
        assert Path(path).exists()

    def test_only_ai_summary(self, output_pdf):
        data = {
            "title": "Summary Only",
            "ai_summary": "This dataset is interesting.\n\nIt has many features.",
        }
        path = generate_report(data, output_pdf)
        assert Path(path).exists()

    def test_full_report_bigger_than_minimal(
        self, full_report_data, minimal_report_data, tmp_path
    ):
        p_full = tmp_path / "full.pdf"
        p_min = tmp_path / "minimal.pdf"
        generate_report(full_report_data, p_full)
        generate_report(minimal_report_data, p_min)
        assert p_full.stat().st_size > p_min.stat().st_size


# ---------------------------------------------------------------------------
# Tests – New sections
# ---------------------------------------------------------------------------
class TestAIInsights:
    def test_pre_provided_insights(self, output_pdf):
        data = {
            "title": "Insight Test",
            "ai_insights": "Revenue is growing steadily.",
            "eda_summary": {
                "descriptive_stats": {
                    "X": {"count": 10, "mean": 5.0, "std": 2.0, "min": 1, "max": 10}
                },
            },
        }
        path = generate_report(data, output_pdf)
        assert Path(path).exists()

    def test_fallback_when_ollama_unavailable(self, output_pdf):
        data = {
            "title": "No Ollama",
            "eda_summary": {
                "descriptive_stats": {
                    "X": {"count": 10, "mean": 5.0, "std": 2.0, "min": 1, "max": 10}
                },
            },
        }
        # No ai_insights key and Ollama isn't running → should still build
        with patch(
            "modules.report_gen._generate_ai_text", return_value=None
        ):
            path = generate_report(data, output_pdf)
        assert Path(path).exists()


class TestConclusion:
    def test_pre_provided_conclusion(self, output_pdf):
        data = {
            "title": "Conclusion Test",
            "ai_summary": "Test summary.",
            "conclusion": "Key finding.\n\nNext step: deploy.",
        }
        path = generate_report(data, output_pdf)
        assert Path(path).exists()

    def test_fallback_when_ollama_unavailable(self, output_pdf):
        data = {
            "title": "No Ollama",
            "ai_summary": "Some analysis.",
        }
        with patch(
            "modules.report_gen._generate_ai_text", return_value=None
        ):
            path = generate_report(data, output_pdf)
        assert Path(path).exists()


class TestVisualizations:
    def test_heatmap_generated(self):
        eda = {
            "correlation_matrix": {
                "matrix": {
                    "A": {"A": 1.0, "B": 0.5},
                    "B": {"A": 0.5, "B": 1.0},
                }
            }
        }
        result = _render_correlation_heatmap(eda)
        assert result is not None
        assert result[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes

    def test_heatmap_returns_none_for_single_col(self):
        eda = {
            "correlation_matrix": {
                "matrix": {"A": {"A": 1.0}}
            }
        }
        assert _render_correlation_heatmap(eda) is None

    def test_heatmap_returns_none_for_missing_data(self):
        assert _render_correlation_heatmap({}) is None

    def test_distribution_chart_generated(self):
        eda = {
            "descriptive_stats": {
                "X": {"count": 10, "mean": 5.0, "std": 2.0, "min": 1, "max": 10},
                "Y": {"count": 10, "mean": 3.0, "std": 1.5, "min": 0, "max": 8},
            }
        }
        result = _render_distribution_chart(eda)
        assert result is not None
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_distribution_returns_none_for_no_numeric(self):
        eda = {
            "descriptive_stats": {
                "Cat": {"count": 10, "unique": 3, "top": "A", "freq": 5}
            }
        }
        assert _render_distribution_chart(eda) is None

    def test_charts_embedded_in_pdf(self, full_report_data, output_pdf):
        path = generate_report(full_report_data, output_pdf)
        # Full data has correlation matrix → PDF should be larger
        assert output_pdf.stat().st_size > 5000


# ---------------------------------------------------------------------------
# Tests – Prompt builders
# ---------------------------------------------------------------------------
class TestPromptBuilders:
    def test_insights_prompt_has_stats(self):
        eda = {
            "descriptive_stats": {
                "Price": {"count": 100, "mean": 50.0, "std": 10.0, "min": 5, "max": 99}
            },
            "missing_values": {"total_missing": 5, "columns": {}},
            "outliers": {"total_outlier_rows": 3},
        }
        prompt = _build_insights_prompt(eda)
        assert "Price" in prompt
        assert "mean=" in prompt

    def test_conclusion_prompt_includes_context(self):
        data = {
            "eda_summary": {"key_findings": ["Revenue growing"]},
            "ml_comparison": {"best_model": "RF"},
            "ai_summary": "Good results.",
        }
        prompt = _build_conclusion_prompt(data)
        assert "Revenue growing" in prompt
        assert "RF" in prompt


# ---------------------------------------------------------------------------
# Tests – Helpers
# ---------------------------------------------------------------------------
class TestHelpers:
    def test_fmt_none(self):
        assert _fmt(None) == "N/A"

    def test_fmt_small_float(self):
        assert _fmt(0.1234) == "0.1234"

    def test_fmt_large_float(self):
        assert _fmt(1234.5678) == "1,234.57"

    def test_fmt_int(self):
        assert _fmt(42) == "42"

    def test_title_case(self):
        assert _title_case("f1_score") == "F1 Score"
        assert _title_case("accuracy") == "Accuracy"


# ---------------------------------------------------------------------------
# Tests – Validation
# ---------------------------------------------------------------------------
class TestValidation:
    def test_none_raises(self):
        with pytest.raises(ValueError, match="dict"):
            generate_report(None)

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="dict"):
            generate_report("not a dict")

    def test_empty_dict_ok(self, output_pdf):
        path = generate_report({}, output_pdf)
        assert Path(path).exists()
