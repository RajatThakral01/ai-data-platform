"""Tests for modules.report_gen."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.report_gen import generate_report


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
            "transactions that could be worth investigating for upselling "
            "opportunities.\n\n"
            "The Random Forest model achieved the best prediction accuracy with "
            "an R² score of 0.92, suggesting that the features strongly explain "
            "revenue variation."
        ),
    }


@pytest.fixture()
def minimal_report_data() -> dict:
    return {"title": "Minimal Report"}


@pytest.fixture()
def output_pdf(tmp_path: Path) -> Path:
    return tmp_path / "test_report.pdf"


# ---------------------------------------------------------------------------
# Tests
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
