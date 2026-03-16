"""
data_loader.py – Robust CSV / Excel loader for the AI Data Platform.

Usage:
    from modules.data_loader import load_data

    df, summary = load_data("path/to/file.csv")
    df, summary = load_data("path/to/report.xlsx", sheet_name="Q1")

Returns:
    tuple[pd.DataFrame, dict]
        - A cleaned DataFrame (whitespace-stripped headers, duplicate rows dropped).
        - A summary dict with shape, columns, dtypes, missing-value counts,
          and duplicate-row count *before* deduplication.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported extensions
# ---------------------------------------------------------------------------
_CSV_EXTENSIONS = {".csv", ".tsv", ".txt"}
_EXCEL_EXTENSIONS = {".xls", ".xlsx", ".xlsm", ".xlsb"}
_SUPPORTED_EXTENSIONS = _CSV_EXTENSIONS | _EXCEL_EXTENSIONS


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class DataLoaderError(Exception):
    """Base exception for all data-loading errors."""


class FileNotFoundError_(DataLoaderError):
    """Raised when the target file does not exist."""


class UnsupportedFileTypeError(DataLoaderError):
    """Raised when the file extension is not supported."""


class EmptyFileError(DataLoaderError):
    """Raised when the file is empty or contains no parseable rows."""


class FileParsingError(DataLoaderError):
    """Raised when Pandas cannot parse the file content."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _validate_file(filepath: str | Path) -> Path:
    """Validate that *filepath* exists, is a file, and has a supported extension.

    Returns the resolved ``Path`` object.

    Raises:
        FileNotFoundError_: if the path does not exist or is not a file.
        UnsupportedFileTypeError: if the extension is not supported.
    """
    path = Path(filepath).resolve()

    if not path.exists():
        raise FileNotFoundError_(f"File not found: {path}")
    if not path.is_file():
        raise FileNotFoundError_(f"Path is not a file: {path}")

    ext = path.suffix.lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{ext}'. "
            f"Supported types: {sorted(_SUPPORTED_EXTENSIONS)}"
        )
    return path


def _read_file(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame.

    Extra ``**kwargs`` are forwarded to the underlying Pandas reader so callers
    can pass ``sheet_name``, ``encoding``, ``sep``, etc.

    Raises:
        FileParsingError: if Pandas cannot parse the file.
        EmptyFileError: if the resulting DataFrame is completely empty.
    """
    ext = path.suffix.lower()

    try:
        if ext in _CSV_EXTENSIONS:
            sep = kwargs.pop("sep", None)
            if sep is None:
                sep = "\t" if ext == ".tsv" else ","
            df = pd.read_csv(path, sep=sep, **kwargs)
        else:
            engine = "xlrd" if ext == ".xls" else "openpyxl"
            df = pd.read_excel(path, engine=engine, **kwargs)
    except Exception as exc:
        raise FileParsingError(f"Failed to parse '{path.name}': {exc}") from exc

    if df.empty:
        raise EmptyFileError(f"File '{path.name}' produced an empty DataFrame.")

    return df


def _clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Apply lightweight cleaning to *df*.

    Cleaning steps:
        1. Strip leading/trailing whitespace from column names.
        2. Drop fully-duplicated rows and report how many were removed.

    Returns:
        (cleaned_df, duplicate_count_before_drop)
    """
    # 1. Normalise column names
    df.columns = df.columns.str.strip()

    # 2. Count and drop duplicates
    duplicate_count = int(df.duplicated().sum())
    if duplicate_count > 0:
        logger.info("Dropping %d duplicate row(s).", duplicate_count)
        df = df.drop_duplicates().reset_index(drop=True)

    return df, duplicate_count


def _build_summary(df: pd.DataFrame, duplicate_count: int) -> dict[str, Any]:
    """Build a summary dictionary describing *df*.

    Keys:
        shape            – (rows, cols) tuple *after* cleaning.
        columns          – list of column names.
        dtypes           – dict mapping column name → dtype string.
        missing_values   – dict mapping column name → count of NaN/None values.
        duplicate_count  – number of duplicate rows found *before* cleaning.
    """
    return {
        "shape": df.shape,
        "columns": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_values": df.isna().sum().to_dict(),
        "duplicate_count": duplicate_count,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def load_data(
    filepath: str | Path,
    **kwargs: Any,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load, validate, clean, and summarise a CSV or Excel file.

    Parameters
    ----------
    filepath : str | Path
        Path to the data file.
    **kwargs
        Extra keyword arguments forwarded to :func:`pandas.read_csv` or
        :func:`pandas.read_excel` (e.g. ``sheet_name``, ``encoding``,
        ``sep``, ``dtype``).

    Returns
    -------
    tuple[pd.DataFrame, dict]
        ``(cleaned_dataframe, summary_dict)``

    Raises
    ------
    FileNotFoundError_
        If the file does not exist.
    UnsupportedFileTypeError
        If the file extension is not CSV or Excel.
    EmptyFileError
        If the file is empty after parsing.
    FileParsingError
        If Pandas cannot parse the file.

    Examples
    --------
    >>> df, summary = load_data("sales.csv")
    >>> print(summary["shape"])
    (1000, 12)
    """
    logger.info("Loading file: %s", filepath)

    # Step 1 – Validate
    path = _validate_file(filepath)

    # Step 2 – Read
    df = _read_file(path, **kwargs)
    logger.info("Raw shape: %s", df.shape)

    # Step 3 – Clean
    df, dup_count = _clean_dataframe(df)

    # Step 4 – Summarise
    summary = _build_summary(df, dup_count)
    logger.info(
        "Loaded %d rows × %d cols (%d duplicates removed).",
        summary["shape"][0],
        summary["shape"][1],
        dup_count,
    )

    return df, summary
