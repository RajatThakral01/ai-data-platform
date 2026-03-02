"""Tests for modules.data_loader."""

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from modules.data_loader import (
    DataLoaderError,
    EmptyFileError,
    FileNotFoundError_,
    FileParsingError,
    UnsupportedFileTypeError,
    load_data,
)


# ---------------------------------------------------------------------------
# Fixtures – tiny files written to a temp directory
# ---------------------------------------------------------------------------
@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def sample_csv(tmp_dir: Path) -> Path:
    path = tmp_dir / "sample.csv"
    df = pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "Charlie", "Alice"],
            "Age": [30, 25, 35, 30],
            "Score": [88.5, 92.0, None, 88.5],
        }
    )
    df.to_csv(path, index=False)
    return path


@pytest.fixture()
def sample_xlsx(tmp_dir: Path) -> Path:
    path = tmp_dir / "sample.xlsx"
    df = pd.DataFrame(
        {
            " Name ": ["Alice", "Bob"],
            "Value": [100, 200],
        }
    )
    df.to_excel(path, index=False)
    return path


@pytest.fixture()
def empty_csv(tmp_dir: Path) -> Path:
    path = tmp_dir / "empty.csv"
    path.write_text("Name,Age\n")  # headers only → empty DataFrame
    return path


@pytest.fixture()
def tsv_file(tmp_dir: Path) -> Path:
    path = tmp_dir / "data.tsv"
    path.write_text("col1\tcol2\n1\t2\n3\t4\n")
    return path


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------
class TestLoadCSV:
    def test_returns_dataframe_and_summary(self, sample_csv: Path):
        df, summary = load_data(sample_csv)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(summary, dict)

    def test_shape_after_dedup(self, sample_csv: Path):
        df, summary = load_data(sample_csv)
        # Original has 4 rows, 1 duplicate → 3 unique rows
        assert df.shape == (3, 3)
        assert summary["shape"] == (3, 3)

    def test_duplicate_count(self, sample_csv: Path):
        _, summary = load_data(sample_csv)
        assert summary["duplicate_count"] == 1

    def test_missing_values(self, sample_csv: Path):
        _, summary = load_data(sample_csv)
        # After dedup, only one missing Score remains (Charlie's)
        assert summary["missing_values"]["Score"] == 1

    def test_columns_list(self, sample_csv: Path):
        _, summary = load_data(sample_csv)
        assert summary["columns"] == ["Name", "Age", "Score"]

    def test_dtypes_present(self, sample_csv: Path):
        _, summary = load_data(sample_csv)
        assert "Age" in summary["dtypes"]
        assert summary["dtypes"]["Age"] == "int64"


class TestLoadExcel:
    def test_loads_xlsx(self, sample_xlsx: Path):
        df, summary = load_data(sample_xlsx)
        assert df.shape == (2, 2)

    def test_strips_column_names(self, sample_xlsx: Path):
        _, summary = load_data(sample_xlsx)
        assert "Name" in summary["columns"]  # was " Name " in raw file


class TestLoadTSV:
    def test_tsv_auto_detected(self, tsv_file: Path):
        df, _ = load_data(tsv_file)
        assert list(df.columns) == ["col1", "col2"]
        assert len(df) == 2


# ---------------------------------------------------------------------------
# Error-handling tests
# ---------------------------------------------------------------------------
class TestValidationErrors:
    def test_file_not_found(self, tmp_dir: Path):
        with pytest.raises(FileNotFoundError_):
            load_data(tmp_dir / "no_such_file.csv")

    def test_directory_not_file(self, tmp_dir: Path):
        with pytest.raises(FileNotFoundError_):
            load_data(tmp_dir)

    def test_unsupported_extension(self, tmp_dir: Path):
        bad = tmp_dir / "data.json"
        bad.write_text("{}")
        with pytest.raises(UnsupportedFileTypeError):
            load_data(bad)

    def test_empty_file(self, empty_csv: Path):
        with pytest.raises(EmptyFileError):
            load_data(empty_csv)

    def test_corrupt_file(self, tmp_dir: Path):
        bad = tmp_dir / "corrupt.xlsx"
        bad.write_bytes(b"\x00\x01\x02\x03")
        with pytest.raises(FileParsingError):
            load_data(bad)

    def test_all_inherit_from_base(self):
        for exc_cls in (
            FileNotFoundError_,
            UnsupportedFileTypeError,
            EmptyFileError,
            FileParsingError,
        ):
            assert issubclass(exc_cls, DataLoaderError)
