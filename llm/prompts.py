"""
prompts.py – Compressed prompt templates for the AI Data Platform.

Minimal-token prompts that preserve instruction quality.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers – compact data summarisation (≤500 tokens)
# ---------------------------------------------------------------------------
def _compact_summary(summary: dict[str, Any], max_cols: int = 20) -> str:
    """Build a ≤500-token dataset summary for LLM context.

    Includes: column names+types, top-5 stats, missing %, top-3 categorical
    values, notable correlations.
    """
    desc = summary.get("descriptive_stats", {})
    mv = summary.get("missing_values", {})
    mv_cols = mv.get("columns", {})

    lines: list[str] = []

    # Shape
    n_rows: int | str = "?"
    for stats in desc.values():
        if "count" in stats:
            n_rows = int(stats["count"])
            break
    lines.append(f"Shape: {n_rows} rows × {len(desc)} cols")

    # Per-column: name, type, key stats, missing%
    for i, (col, stats) in enumerate(desc.items()):
        if i >= max_cols:
            lines.append(f"  ... +{len(desc) - max_cols} more cols")
            break

        mv_info = mv_cols.get(col, {})
        miss_pct = mv_info.get("percentage", 0)

        if "mean" in stats:
            # Numeric
            parts = [
                f"mean={stats.get('mean', '?'):.4g}",
                f"std={stats.get('std', '?'):.4g}",
                f"min={stats.get('min', '?')}",
                f"max={stats.get('max', '?')}",
            ]
            if miss_pct:
                parts.append(f"miss={miss_pct}%")
            lines.append(f"  {col}(num): {', '.join(parts)}")
        elif "unique" in stats:
            # Categorical
            top_vals = stats.get("top", "?")
            parts = [f"unique={stats['unique']}"]
            if top_vals != "?":
                parts.append(f"top='{top_vals}'")
            if miss_pct:
                parts.append(f"miss={miss_pct}%")
            lines.append(f"  {col}(cat): {', '.join(parts)}")
        else:
            lines.append(f"  {col}(unk)")

    # Correlations (top 3 by |r|)
    matrix = summary.get("correlation_matrix", {}).get("matrix", {})
    if matrix:
        pairs: list[tuple[str, str, float]] = []
        seen: set[tuple[str, str]] = set()
        for a, row in matrix.items():
            for b, r in row.items():
                if a == b or r is None:
                    continue
                p = tuple(sorted((a, b)))
                if p not in seen and abs(r) >= 0.5:
                    seen.add(p)
                    pairs.append((a, b, r))
        pairs.sort(key=lambda t: abs(t[2]), reverse=True)
        if pairs:
            lines.append("Correlations:")
            for a, b, r in pairs[:3]:
                lines.append(f"  {a}↔{b}: r={r:.2f}")

    # Outliers summary (count only)
    outliers = summary.get("outliers", {})
    total_out = outliers.get("total_outlier_rows", 0)
    if total_out:
        lines.append(f"Outlier rows (IQR): {total_out}")

    return "\n".join(lines)


def _col_list(summary: dict[str, Any]) -> str:
    """Minimal column list: name(type) for code prompts."""
    desc = summary.get("descriptive_stats", {})
    parts: list[str] = []
    for col, stats in desc.items():
        t = "num" if "mean" in stats else ("cat" if "unique" in stats else "?")
        parts.append(f"{col}({t})")
    return ", ".join(parts) if parts else "(no columns)"


# ---------------------------------------------------------------------------
# 1. Narrative prompt
# ---------------------------------------------------------------------------
def narrative_prompt(summary: dict[str, Any]) -> str:
    """Compressed EDA narrative prompt (≤500 token context)."""
    if not summary:
        raise ValueError("EDA summary cannot be None or empty.")

    data = _compact_summary(summary)

    return f"""\
Role: senior data analyst. Write 3-4 paragraph plain-English narrative for non-technical audience.
Cover: (1) what dataset represents (2) size & column types (3) data quality (missing, outliers) (4) key stats & relationships (5) caveats.
Be specific with numbers. No code.

DATA:
{data}"""


# ---------------------------------------------------------------------------
# 2. ML recommendation prompt
# ---------------------------------------------------------------------------
def ml_recommendation_prompt(
    summary: dict[str, Any],
    *,
    target_column: str | None = None,
    task_hint: str | None = None,
) -> str:
    """Compressed ML recommendation prompt."""
    if not summary:
        raise ValueError("EDA summary cannot be None or empty.")

    data = _compact_summary(summary)
    target_line = ""
    if target_column:
        target_line += f"\nTarget: {target_column}"
    if task_hint:
        target_line += f"\nTask: {task_hint}"

    return f"""\
Role: ML engineer. Recommend 2-3 models for this data.
Per model: name, why it fits, preprocessing needed, evaluation metric.
Order simple→complex. Be concise.{target_line}

DATA:
{data}"""


# ---------------------------------------------------------------------------
# 3. NL → Pandas code prompt
# ---------------------------------------------------------------------------
def nl_to_pandas_prompt(
    summary: dict[str, Any],
    question: str,
    *,
    dataframe_name: str = "df",
) -> str:
    """Compressed NL-to-Pandas prompt. Keeps full instruction quality."""
    if not summary:
        raise ValueError("EDA summary cannot be None or empty.")
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    cols = _col_list(summary)
    mv = summary.get("missing_values", {})
    missing_cols = [
        c for c, info in mv.get("columns", {}).items()
        if info.get("count", 0) > 0
    ]
    miss_note = f"Missing in: {', '.join(missing_cols)}" if missing_cols else "No missing values"

    return f"""\
DataFrame `{dataframe_name}` columns: {cols}
{miss_note}

Question: {question.strip()}

Write Pandas code. Rules:
1. Use `{dataframe_name}` only — no file loading
2. Store answer in `result`
3. Handle missing values with .dropna()/.fillna()
4. Split complex operations into named steps — no chained boolean+indexing
5. Return ONLY code block, no explanation

```python
# code here
```"""


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------
PROMPT_CATALOGUE: dict[str, callable] = {
    "narrative": narrative_prompt,
    "ml_recommendation": ml_recommendation_prompt,
    "nl_to_pandas": nl_to_pandas_prompt,
}
