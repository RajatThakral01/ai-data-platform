"""Tests for modules.nl_query.

Tests cover code extraction, sandboxed execution, timeout handling,
and the end-to-end ``ask`` flow (with the LLM mocked).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from modules.nl_query import (
    CodeExecutionError,
    CodeGenerationError,
    ExecutionTimeoutError,
    NLQueryError,
    ask,
    execute_generated_code,
    extract_code,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "Charlie", "Diana"],
            "Age": [30, 25, 35, 28],
            "Salary": [70000, 50000, 90000, 60000],
        }
    )


# ---------------------------------------------------------------------------
# extract_code
# ---------------------------------------------------------------------------
class TestExtractCode:
    def test_fenced_python_block(self):
        response = "Here is the code:\n```python\nresult = df.head()\n```\nDone."
        assert extract_code(response) == "result = df.head()"

    def test_fenced_block_no_language(self):
        response = "```\nresult = 42\n```"
        assert extract_code(response) == "result = 42"

    def test_multiple_blocks_picks_longest(self):
        response = (
            "```python\nx = 1\n```\n"
            "```python\n# full solution\nresult = df.groupby('A').sum()\n```"
        )
        code = extract_code(response)
        assert "groupby" in code

    def test_no_block_falls_back(self):
        response = "result = df['Age'].mean()"
        assert extract_code(response) == "result = df['Age'].mean()"

    def test_empty_raises(self):
        with pytest.raises(CodeGenerationError):
            extract_code("")

    def test_none_raises(self):
        with pytest.raises(CodeGenerationError):
            extract_code(None)

    def test_whitespace_only_raises(self):
        with pytest.raises(CodeGenerationError):
            extract_code("   \n  ")


# ---------------------------------------------------------------------------
# execute_generated_code
# ---------------------------------------------------------------------------
class TestExecuteGeneratedCode:
    def test_simple_result(self, sample_df: pd.DataFrame):
        code = "result = df['Age'].mean()"
        out = execute_generated_code(code, sample_df)
        assert out["success"] is True
        assert out["result"] == pytest.approx(29.5)
        assert out["code"] == code

    def test_pandas_operations(self, sample_df: pd.DataFrame):
        code = "result = df[df['Salary'] > 60000]['Name'].tolist()"
        out = execute_generated_code(code, sample_df)
        assert out["success"] is True
        assert set(out["result"]) == {"Alice", "Charlie"}

    def test_numpy_available(self, sample_df: pd.DataFrame):
        code = "result = float(np.mean(df['Age'].values))"
        out = execute_generated_code(code, sample_df)
        assert out["success"] is True
        assert out["result"] == pytest.approx(29.5)

    def test_missing_result_var(self, sample_df: pd.DataFrame):
        code = "x = df['Age'].mean()"
        out = execute_generated_code(code, sample_df)
        assert out["success"] is False
        assert "result" in out["error"]

    def test_runtime_error_caught(self, sample_df: pd.DataFrame):
        code = "result = df['NonExistent'].mean()"
        out = execute_generated_code(code, sample_df)
        assert out["success"] is False
        assert "error" in out["error"].lower()

    def test_does_not_mutate_original(self, sample_df: pd.DataFrame):
        original_len = len(sample_df)
        code = "df.drop(df.index, inplace=True)\nresult = len(df)"
        execute_generated_code(code, sample_df)
        assert len(sample_df) == original_len  # original untouched

    def test_timeout_on_infinite_loop(self, sample_df: pd.DataFrame):
        code = "while True: pass\nresult = 1"
        out = execute_generated_code(code, sample_df, timeout=1)
        assert out["success"] is False
        assert "timeout" in out["error"].lower()

    def test_custom_df_name(self, sample_df: pd.DataFrame):
        code = "result = data['Age'].max()"
        out = execute_generated_code(code, sample_df, df_name="data")
        assert out["success"] is True
        assert out["result"] == 35

    def test_empty_code_raises(self, sample_df: pd.DataFrame):
        with pytest.raises(ValueError, match="empty"):
            execute_generated_code("", sample_df)

    def test_none_df_raises(self):
        with pytest.raises(ValueError, match="DataFrame"):
            execute_generated_code("result = 1", None)


# ---------------------------------------------------------------------------
# ask (end-to-end with mocked LLM)
# ---------------------------------------------------------------------------
class TestAsk:
    def _mock_llm(self, response_text: str):
        """Return a patcher that replaces get_llm_response in nl_query's namespace."""
        patcher = patch("modules.nl_query.get_llm_response")
        mock_router = patcher.start()
        mock_router.return_value = (
            response_text,
            {"backend_used": "groq", "model_used": "llama-3.3-70b-versatile", "fallback_warning": None},
        )
        return patcher, mock_router

    def test_success(self, sample_df: pd.DataFrame):
        patcher, _ = self._mock_llm(
            "```python\nresult = df['Salary'].max()\n```"
        )
        try:
            out = ask(sample_df, "What is the highest salary?")
            assert out["success"] is True
            assert out["result"] == 90000
            assert "max" in out["code"]
            assert out["error"] is None
        finally:
            patcher.stop()

    def test_llm_failure(self, sample_df: pd.DataFrame):
        patcher = patch("modules.nl_query.get_llm_response")
        mock_router = patcher.start()
        mock_router.side_effect = RuntimeError("both backends failed")
        try:
            out = ask(sample_df, "Count rows")
            assert out["success"] is False
            assert "LLM error" in out["error"]
        finally:
            patcher.stop()

    def test_bad_code_from_llm(self, sample_df: pd.DataFrame):
        patcher, _ = self._mock_llm(
            "```python\nresult = df['NOPE'].sum()\n```"
        )
        try:
            out = ask(sample_df, "Sum of NOPE?")
            assert out["success"] is False
            assert out["code"] is not None  # code was extracted but failed
        finally:
            patcher.stop()

    def test_empty_question_raises(self, sample_df: pd.DataFrame):
        with pytest.raises(ValueError, match="empty"):
            ask(sample_df, "")

    def test_empty_df_raises(self):
        with pytest.raises(ValueError, match="empty"):
            ask(pd.DataFrame(), "anything")

    def test_none_df_raises(self):
        with pytest.raises(ValueError, match="DataFrame"):
            ask(None, "anything")


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------
class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        for cls in (CodeGenerationError, CodeExecutionError, ExecutionTimeoutError):
            assert issubclass(cls, NLQueryError)
