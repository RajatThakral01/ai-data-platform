"""
prompts.py – Prompt templates for the AI Data Platform.

Each function accepts an EDA summary dictionary (as returned by
``modules.eda.run_eda``) and returns a fully-formatted prompt string
ready to be sent to a local Mistral 7B model via ``llm.ollama_client``.

Three prompt builders are provided:

1. **narrative_prompt**   – asks the model to tell the "story" of the dataset
                            in plain English.
2. **ml_recommendation_prompt** – asks the model to recommend suitable ML
                                   models / approaches for the data.
3. **nl_to_pandas_prompt** – asks the model to translate a natural-language
                              question into executable Pandas code.

Usage:
    from modules.eda import run_eda
    from llm.prompts import narrative_prompt, ml_recommendation_prompt, nl_to_pandas_prompt
    from llm.ollama_client import query_model

    results = run_eda(df)

    prompt = narrative_prompt(results)
    answer = query_model(prompt)
"""

from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _format_shape(summary: dict[str, Any]) -> str:
    """Human-readable shape string from the EDA summary."""
    desc = summary.get("descriptive_stats", {})
    mv = summary.get("missing_values", {})
    shape = mv.get("columns", {})
    n_cols = len(shape)
    # Infer row count from any numeric stat's "count", else fall back
    n_rows: int | str = "unknown"
    for col_stats in desc.values():
        if "count" in col_stats:
            n_rows = int(col_stats["count"])
            break
    return f"{n_rows} rows × {n_cols} columns"


def _format_columns_and_types(summary: dict[str, Any]) -> str:
    """Bulleted list of columns with their dtypes."""
    desc = summary.get("descriptive_stats", {})
    lines: list[str] = []
    for col, stats in desc.items():
        # Try to infer type category
        if "mean" in stats:
            kind = "numeric"
        elif "unique" in stats:
            kind = "categorical"
        else:
            kind = "unknown"
        lines.append(f"  - {col} ({kind})")
    return "\n".join(lines) if lines else "  (no columns detected)"


def _format_missing(summary: dict[str, Any]) -> str:
    """Summarise missing values."""
    mv = summary.get("missing_values", {})
    total = mv.get("total_missing", 0)
    if total == 0:
        return "No missing values."

    cols = mv.get("columns", {})
    affected = {
        col: info for col, info in cols.items() if info.get("count", 0) > 0
    }
    parts = [f"Total missing cells: {total}."]
    for col, info in affected.items():
        parts.append(f"  - {col}: {info['count']} ({info['percentage']}%)")
    return "\n".join(parts)


def _format_correlations(summary: dict[str, Any]) -> str:
    """Top correlations (|r| ≥ 0.5, excluding self-correlation)."""
    matrix = summary.get("correlation_matrix", {}).get("matrix", {})
    if not matrix:
        return "Not enough numeric columns for correlation analysis."

    pairs_seen: set[tuple[str, str]] = set()
    notable: list[tuple[str, str, float]] = []

    for col_a, row in matrix.items():
        for col_b, r in row.items():
            if col_a == col_b:
                continue
            pair = tuple(sorted((col_a, col_b)))
            if pair in pairs_seen:
                continue
            pairs_seen.add(pair)
            if r is not None and abs(r) >= 0.5:
                notable.append((col_a, col_b, r))

    if not notable:
        return "No strong correlations (|r| ≥ 0.5) detected."

    notable.sort(key=lambda t: abs(t[2]), reverse=True)
    lines = [f"  - {a} ↔ {b}: r = {r:.2f}" for a, b, r in notable]
    return "Notable correlations:\n" + "\n".join(lines)


def _format_outliers(summary: dict[str, Any]) -> str:
    """Summarise IQR outlier results."""
    outliers = summary.get("outliers", {})
    total_rows = outliers.get("total_outlier_rows", 0)
    if total_rows == 0:
        return "No outliers detected via IQR method."

    cols = outliers.get("columns", {})
    lines = [f"Total rows with at least one outlier: {total_rows}."]
    for col, info in cols.items():
        cnt = info.get("outlier_count", 0)
        if cnt > 0:
            lb = info.get("lower_bound")
            ub = info.get("upper_bound")
            lines.append(
                f"  - {col}: {cnt} outlier(s)  "
                f"(IQR fence: [{lb}, {ub}])"
            )
    return "\n".join(lines)


def _format_descriptive_stats(summary: dict[str, Any]) -> str:
    """Compact JSON of descriptive stats (truncated for prompt brevity)."""
    desc = summary.get("descriptive_stats", {})
    if not desc:
        return "{}"
    # Keep it compact but readable
    return json.dumps(desc, indent=2, default=str)


def _build_dataset_context(summary: dict[str, Any]) -> str:
    """Assemble the common 'dataset context' block reused across prompts."""
    sections = [
        f"## Dataset Overview\n{_format_shape(summary)}",
        f"## Columns\n{_format_columns_and_types(summary)}",
        f"## Missing Values\n{_format_missing(summary)}",
        f"## Correlations\n{_format_correlations(summary)}",
        f"## Outliers\n{_format_outliers(summary)}",
    ]
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# 1. Narrative prompt
# ---------------------------------------------------------------------------
def narrative_prompt(summary: dict[str, Any]) -> str:
    """Return a prompt that asks the model to narrate the dataset in plain English.

    Parameters
    ----------
    summary : dict
        The dictionary returned by ``modules.eda.run_eda``.

    Returns
    -------
    str
        Formatted prompt string.

    Raises
    ------
    ValueError
        If *summary* is ``None`` or empty.
    """
    if not summary:
        raise ValueError("EDA summary cannot be None or empty.")

    context = _build_dataset_context(summary)
    stats_json = _format_descriptive_stats(summary)

    return f"""\
You are a senior data analyst. Below is an automated EDA summary of a dataset.
Write a clear, plain-English narrative (3–5 paragraphs) that a non-technical
stakeholder could understand. Cover:

1. What the dataset appears to represent.
2. Its size and the types of information it contains.
3. Data-quality observations (missing values, duplicates, outliers).
4. Key statistical highlights and notable relationships between variables.
5. Any caveats or limitations.

---

{context}

## Descriptive Statistics (JSON)
```json
{stats_json}
```

---

Write your narrative now."""


# ---------------------------------------------------------------------------
# 2. ML recommendation prompt
# ---------------------------------------------------------------------------
def ml_recommendation_prompt(
    summary: dict[str, Any],
    *,
    target_column: str | None = None,
    task_hint: str | None = None,
) -> str:
    """Return a prompt that asks the model to recommend ML models for the data.

    Parameters
    ----------
    summary : dict
        The dictionary returned by ``modules.eda.run_eda``.
    target_column : str | None
        If known, the column the user wants to predict.
    task_hint : str | None
        Optional hint like ``"classification"``, ``"regression"``,
        ``"clustering"``, or ``"anomaly detection"``.

    Returns
    -------
    str
        Formatted prompt string.

    Raises
    ------
    ValueError
        If *summary* is ``None`` or empty.
    """
    if not summary:
        raise ValueError("EDA summary cannot be None or empty.")

    context = _build_dataset_context(summary)
    stats_json = _format_descriptive_stats(summary)

    target_section = ""
    if target_column:
        target_section += f"\n**Target column:** `{target_column}`"
    if task_hint:
        target_section += f"\n**Suggested task type:** {task_hint}"
    if not target_section:
        target_section = (
            "\nThe user has not specified a target column or task type. "
            "Infer the most likely ML tasks from the data."
        )

    return f"""\
You are a machine-learning engineer. Based on the EDA summary below,
recommend suitable ML models and preprocessing steps.

For each recommendation provide:
- **Model name** and why it fits this data.
- **Preprocessing** steps required (e.g. encoding, scaling, imputation).
- **Expected challenges** (e.g. class imbalance, high cardinality, outliers).
- **Evaluation metrics** to use.

List at least 2 and at most 4 recommendations, ordered from simplest to
most complex.
{target_section}

---

{context}

## Descriptive Statistics (JSON)
```json
{stats_json}
```

---

Provide your recommendations now."""


# ---------------------------------------------------------------------------
# 3. Natural-language → Pandas code prompt
# ---------------------------------------------------------------------------
def nl_to_pandas_prompt(
    summary: dict[str, Any],
    question: str,
    *,
    dataframe_name: str = "df",
) -> str:
    """Return a prompt that asks the model to translate *question* into Pandas code.

    Parameters
    ----------
    summary : dict
        The dictionary returned by ``modules.eda.run_eda``.
    question : str
        The user's natural-language question about the data.
    dataframe_name : str
        Variable name of the DataFrame in the generated code (default ``"df"``).

    Returns
    -------
    str
        Formatted prompt string.

    Raises
    ------
    ValueError
        If *summary* is ``None``/empty or *question* is blank.
    """
    if not summary:
        raise ValueError("EDA summary cannot be None or empty.")
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    # For the code prompt we only need columns + types, not full stats
    col_lines: list[str] = []
    desc = summary.get("descriptive_stats", {})
    for col, stats in desc.items():
        if "mean" in stats:
            kind = "numeric"
        elif "unique" in stats:
            kind = "categorical"
        else:
            kind = "unknown"
        col_lines.append(f"  - `{col}` ({kind})")

    columns_block = "\n".join(col_lines) if col_lines else "  (no column info)"

    mv = summary.get("missing_values", {})
    missing_cols = [
        col
        for col, info in mv.get("columns", {}).items()
        if info.get("count", 0) > 0
    ]
    missing_note = (
        f"Columns with missing values: {', '.join(missing_cols)}."
        if missing_cols
        else "No missing values."
    )

    return f"""\
You are a Python data-analysis expert. The user has a Pandas DataFrame called
`{dataframe_name}` with the following columns:

{columns_block}

{missing_note}

**User's question:**
> {question.strip()}

Write Python code using Pandas that answers this question. Follow these rules:
1. Use only the `{dataframe_name}` variable — do not load any files.
2. Store the final answer in a variable called `result`.
3. Add brief inline comments explaining each step.
4. Handle potential missing values gracefully (use `.dropna()` or `.fillna()` where appropriate).
5. Return ONLY the code block — no extra explanation.

```python
# Your code here
```"""


# ---------------------------------------------------------------------------
# Catalogue (useful for dynamic dispatch)
# ---------------------------------------------------------------------------
PROMPT_CATALOGUE: dict[str, callable] = {
    "narrative": narrative_prompt,
    "ml_recommendation": ml_recommendation_prompt,
    "nl_to_pandas": nl_to_pandas_prompt,
}
