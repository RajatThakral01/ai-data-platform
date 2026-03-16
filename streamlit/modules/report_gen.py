"""
report_gen.py – Professional PDF report generator for the AI Data Platform.

Uses ReportLab to produce a multi-section PDF report from a single input
dictionary.  Designed to consume the outputs of ``data_loader``, ``eda``,
``ml_engine``, and ``llm`` modules directly.

Sections (numbered automatically):
    1. Dataset Overview
    2. Exploratory Data Analysis (tables + stats)
    3. AI-Generated Narrative Insights   ← NEW (calls Ollama)
    4. Visualizations                     ← NEW (embedded charts)
    5. Machine Learning Model Comparison
    6. AI-Generated Summary
    7. Conclusion & Next Steps            ← NEW (calls Ollama)

Usage:
    from modules.report_gen import generate_report

    report_data = {
        "title": "Sales Analysis Report",
        "author": "AI Data Platform",
        "date": "2026-02-25",
        "dataset_overview": { ... },
        "eda_summary": { ... },
        "ml_comparison": { ... },
        "ai_summary": "The dataset shows ...",
    }
    output_path = generate_report(report_data, "report.pdf")
"""

from __future__ import annotations

import io
import logging
import os
import textwrap
import base64
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import re

def clean_text(text):
    if not text or not isinstance(text, str):
        return ''
    text = re.sub(r'<[^>]+>', '', text)  # Remove ALL XML/HTML tags
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Remove bold markdown
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)  # Remove headers
    text = text.replace('■', '•').replace('\u0001', '').replace('\u0002', '')
    text = ' '.join(text.split())  # Normalize whitespace
    return text.strip()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette – refined professional theme
# ---------------------------------------------------------------------------
_PRIMARY = colors.HexColor("#1a237e")        # deep indigo
_SECONDARY = colors.HexColor("#283593")      # slightly lighter indigo
_ACCENT = colors.HexColor("#3949ab")         # mid-indigo
_ACCENT_LIGHT = colors.HexColor("#7986cb")   # light indigo
_LIGHT_BG = colors.HexColor("#e8eaf6")       # wash background
_TABLE_HEADER = colors.HexColor("#1a237e")
_TABLE_HEADER_TEXT = colors.white
_TABLE_ALT_ROW = colors.HexColor("#f5f5f5")
_TEXT = colors.HexColor("#212121")
_TEXT_SECONDARY = colors.HexColor("#424242")
_MUTED = colors.HexColor("#757575")
_SUCCESS = colors.HexColor("#2e7d32")
_DIVIDER = colors.HexColor("#c5cae9")
_CALLOUT_BG = colors.HexColor("#e8eaf6")
_CALLOUT_BORDER = colors.HexColor("#5c6bc0")

_PAGE_W, _PAGE_H = A4

# ---------------------------------------------------------------------------
# Custom styles – improved typography
# ---------------------------------------------------------------------------
_base_styles = getSampleStyleSheet()


def _get_styles() -> dict[str, ParagraphStyle]:
    """Return a dict of custom ParagraphStyles for the report."""
    return {
        "report_title": ParagraphStyle(
            "ReportTitle",
            parent=_base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=32,
            leading=38,
            textColor=_PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=_base_styles["Normal"],
            fontName="Helvetica",
            fontSize=13,
            leading=17,
            textColor=_MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading",
            parent=_base_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=22,
            textColor=_PRIMARY,
            spaceBefore=24,
            spaceAfter=6,
        ),
        "sub_heading": ParagraphStyle(
            "SubHeading",
            parent=_base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=_SECONDARY,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=_base_styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=_TEXT,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            parent=_base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=15,
            textColor=_TEXT,
            spaceAfter=4,
        ),
        "body_italic": ParagraphStyle(
            "BodyItalic",
            parent=_base_styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=10,
            leading=15,
            textColor=_TEXT_SECONDARY,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=_base_styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=_TEXT,
            leftIndent=24,
            spaceAfter=3,
            bulletIndent=10,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=_base_styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=10,
            leading=15,
            textColor=_SECONDARY,
            alignment=TA_JUSTIFY,
            leftIndent=16,
            rightIndent=16,
            spaceBefore=6,
            spaceAfter=6,
            backColor=_CALLOUT_BG,
            borderColor=_CALLOUT_BORDER,
            borderWidth=1,
            borderPadding=8,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=_base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=_MUTED,
            alignment=TA_CENTER,
        ),
        "kpi_value": ParagraphStyle(
            "KPIValue",
            parent=_base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=_PRIMARY,
            alignment=TA_CENTER,
        ),
        "kpi_label": ParagraphStyle(
            "KPILabel",
            parent=_base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=_MUTED,
            alignment=TA_CENTER,
        ),
    }


# ---------------------------------------------------------------------------
# Decorative helpers
# ---------------------------------------------------------------------------
def _section_divider() -> HRFlowable:
    """Return a styled horizontal rule used between sections."""
    return HRFlowable(
        width="100%",
        thickness=0.5,
        color=_DIVIDER,
        spaceBefore=12,
        spaceAfter=12,
    )


def _kpi_card(value: str, label: str, styles: dict) -> Table:
    """Build a single KPI metric card."""
    data = [
        [Paragraph(clean_text(str(value)), styles["kpi_value"])],
        [Paragraph(clean_text(label), styles["kpi_label"])],
    ]
    card = Table(data, colWidths=[3.8 * cm])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _LIGHT_BG),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, _DIVIDER),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return card


def _kpi_row(pairs: list[tuple[str, str]], styles: dict) -> Table:
    """Build a row of KPI cards from (value, label) pairs."""
    cards = [_kpi_card(v, l, styles) for v, l in pairs]
    n = len(cards)
    available = _PAGE_W - 4 * cm  # left + right margin
    col_w = available / n
    row = Table([cards], colWidths=[col_w] * n)
    row.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return row


# ---------------------------------------------------------------------------
# Table builder helper
# ---------------------------------------------------------------------------
def _build_table(
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[float] | None = None,
) -> Table:
    """Build a styled Table flowable from *headers* and *rows*."""
    data = [headers] + rows
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style_cmds: list[tuple] = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), _TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), _TABLE_HEADER_TEXT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e0e0e0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        # Left-align first column
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (0, -1), 8),
    ]

    # Alternate row shading
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), _TABLE_ALT_ROW))

    table.setStyle(TableStyle(style_cmds))
    return table


# ---------------------------------------------------------------------------
# AI helper – call Ollama for narrative / conclusion
# ---------------------------------------------------------------------------
def _generate_ai_text(
    prompt: str,
    model: str = "mistral",
    host: str = "http://localhost:11434",
    backend: str = "ollama",
    api_key: str | None = None,
    max_tokens: int | None = 300,
    groq_model: str | None = None,
) -> str | None:
    """Call the LLM to generate text.  Returns ``None`` on any failure.

    Uses priority chain: Groq → Gemini → Ollama.
    """
    try:
        from llm.client_factory import get_llm_response, GROQ_MODEL_SMALL
        kwargs: dict = {
            "temperature": 0.4,
            "host": host,
            "max_tokens": max_tokens,
            "groq_model": groq_model or GROQ_MODEL_SMALL,
        }
        text, _meta = get_llm_response(prompt, module_name="report_gen", **kwargs)
        return text
    except Exception as exc:
        logger.warning("AI text generation failed: %s", exc)
        return None


def _build_insights_prompt(eda: dict[str, Any]) -> str:
    """Build a compressed prompt requesting 3-4 sentence narrative insights.

    Filters out irrelevant columns (IDs, geo, counts) before sending to LLM.
    """
    from llm.prompts import _compact_summary
    # Filter EDA to exclude irrelevant columns
    filtered = _filter_eda_columns(eda)
    data = _compact_summary(filtered)
    return (
        "Role: data analyst. Write 3-4 sentences of plain English insights. "
        "Be specific with numbers. No bullet points or headings.\n\n"
        f"DATA:\n{data}\n\nInsights:"
    )


def _build_conclusion_prompt(
    data: dict[str, Any],
) -> str:
    """Build a prompt for the conclusion & next-steps section.

    Includes actual ML model accuracy scores so the LLM doesn't invent numbers.
    """
    parts: list[str] = []

    eda = data.get("eda_summary", {})
    findings = eda.get("key_findings", [])
    if findings:
        parts.append("Key EDA findings:\n" + "\n".join(f"- {f}" for f in findings))

    ml = data.get("ml_comparison", {})
    best = ml.get("best_model")
    if best:
        parts.append(f"Best ML model: {best}")

    # Include actual model scores
    ml_results = ml.get("results", [])
    if ml_results:
        score_lines: list[str] = []
        for entry in ml_results:
            name = entry.get("model", "?")
            metrics = entry.get("metrics", {})
            rank = entry.get("rank", "?")
            metric_strs = [f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                           for k, v in metrics.items()]
            score_lines.append(f"  #{rank} {name}: {', '.join(metric_strs)}")
        parts.append("Model scores (EXACT — use these numbers, do not invent):\n"
                     + "\n".join(score_lines))

    ai_summary = data.get("ai_summary", "")
    if ai_summary:
        parts.append(f"Prior AI summary excerpt: {ai_summary[:300]}")

    context = "\n\n".join(parts) if parts else "(no analysis context)"

    return textwrap.dedent(f"""\
        You are a senior data analyst writing the conclusion of a formal report.
        Based on the analysis context below, write 2 short paragraphs.

        The first paragraph should summarise the key findings in 2-3 sentences.
        The second paragraph should recommend 2-3 concrete next steps.

        IMPORTANT: Do NOT include any labels like "Paragraph 1:" or
        "Paragraph 2:" or "Summary:" or "Next Steps:". Just write clean,
        flowing prose. Be professional, concise, and specific. No bullet points.
        Separate the two paragraphs with a blank line.

        Use only these exact scores from the results, do not invent numbers.

        Analysis context:
        {context}

        Conclusion:""")


# ---------------------------------------------------------------------------
# Chart generation helper
# ---------------------------------------------------------------------------
def _render_correlation_heatmap(eda: dict[str, Any]) -> bytes | None:
    """Render a correlation heatmap as PNG bytes using Matplotlib.

    Returns ``None`` if there aren't enough numeric columns.
    """
    corr_data = eda.get("correlation_matrix", {})
    matrix = corr_data.get("matrix")
    if not matrix or len(matrix) < 2:
        return None

    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt

        columns = list(matrix.keys())
        n = len(columns)
        arr = np.array([[matrix[r].get(c, 0) for c in columns] for r in columns])

        fig, ax = plt.subplots(figsize=(6, 4.5), dpi=150)

        cmap = plt.cm.RdBu_r
        im = ax.imshow(arr, cmap=cmap, vmin=-1, vmax=1, aspect="auto")

        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(columns, fontsize=8, rotation=45, ha="right")
        ax.set_yticklabels(columns, fontsize=8)

        # Annotate cells
        for i in range(n):
            for j in range(n):
                val = arr[i, j]
                color = "white" if abs(val) > 0.65 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=7, color=color)

        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=7)

        ax.set_title("Correlation Heatmap", fontsize=11, fontweight="bold",
                      color="#1a237e", pad=12)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Heatmap generation failed: %s", exc)
        return None


# Column name patterns to exclude from distribution charts and LLM prompts
_EXCLUDED_COL_PATTERNS = {
    "zip", "zipcode", "zip_code", "zip code",
    "latitude", "lat", "longitude", "lon", "lng",
    "lat long", "count", "index",
    "customerid", "customer_id", "customer id",
}
_EXCLUDED_COL_SUFFIXES = ("_id", " id", "id")


def _is_irrelevant_column(col_name: str) -> bool:
    """Return True if a column is likely an ID, geo-coordinate, or irrelevant."""
    lower = col_name.lower().strip()
    if lower in _EXCLUDED_COL_PATTERNS:
        return True
    if lower.endswith(_EXCLUDED_COL_SUFFIXES):
        return True
    if lower.startswith("id"):
        return True
    return False


def _filter_eda_columns(eda: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the EDA summary with irrelevant columns removed."""
    filtered = {}
    for key, value in eda.items():
        if key == "descriptive_stats" and isinstance(value, dict):
            filtered[key] = {
                c: s for c, s in value.items() if not _is_irrelevant_column(c)
            }
        elif key == "missing_values" and isinstance(value, dict):
            mv_copy = dict(value)
            cols = mv_copy.get("columns", {})
            if isinstance(cols, dict):
                mv_copy["columns"] = {
                    c: s for c, s in cols.items() if not _is_irrelevant_column(c)
                }
            filtered[key] = mv_copy
        else:
            filtered[key] = value
    return filtered


def _render_distribution_chart(eda: dict[str, Any]) -> bytes | None:
    """Render a normalized distribution overview for numeric columns (bar chart).

    Excludes irrelevant columns like IDs, zip codes, and geo-coordinates.
    Normalizes values (min-max) so high-magnitude columns like CLTV don't
    dominate the chart.
    Returns ``None`` if no meaningful numeric stats exist.
    """
    desc = eda.get("descriptive_stats", {})
    numeric = {
        c: s for c, s in desc.items()
        if "mean" in s and "min" in s and not _is_irrelevant_column(c)
    }
    if not numeric:
        return None

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        cols = list(numeric.keys())[:8]  # cap at 8 for readability
        means = [numeric[c].get("mean", 0) for c in cols]
        stds = [numeric[c].get("std", 0) for c in cols]

        # Min-max normalize so CLTV doesn't dominate
        max_val = max(abs(m) for m in means) if means else 1
        if max_val == 0:
            max_val = 1
        norm_means = [m / max_val for m in means]
        norm_stds = [s / max_val for s in stds]

        fig, ax = plt.subplots(figsize=(6, 3.5), dpi=150)

        x = range(len(cols))
        bar_colors = ["#3949ab", "#5c6bc0", "#7986cb", "#9fa8da",
                       "#3949ab", "#5c6bc0", "#7986cb", "#9fa8da"]
        ax.bar(x, norm_means, color=bar_colors[:len(cols)], alpha=0.85,
               edgecolor="white", linewidth=0.5)
        ax.errorbar(x, norm_means, yerr=norm_stds, fmt="none", ecolor="#424242",
                     capsize=3, linewidth=1)

        ax.set_xticks(x)
        ax.set_xticklabels(cols, fontsize=8, rotation=30, ha="right")
        ax.set_ylabel("Normalized (0–1)", fontsize=9)
        ax.set_title("Numeric Column Distributions (normalized)", fontsize=11,
                      fontweight="bold", color="#1a237e", pad=12)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Distribution chart generation failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Section builders – each returns a list of Flowable objects
# ---------------------------------------------------------------------------
def _build_title_page(data: dict[str, Any], styles: dict) -> list:
    """Build the title page."""
    elements: list = []
    elements.append(Spacer(1, 4.5 * cm))

    # Decorative line above title
    elements.append(HRFlowable(
        width="40%", thickness=2, color=_ACCENT,
        spaceBefore=0, spaceAfter=16,
    ))

    title = data.get("title", "Data Analysis Report")
    elements.append(Paragraph(clean_text(title), styles["report_title"]))

    # Decorative line below title
    elements.append(HRFlowable(
        width="40%", thickness=2, color=_ACCENT,
        spaceBefore=8, spaceAfter=20,
    ))

    author = data.get("author", "AI Data Platform")
    elements.append(Paragraph(clean_text(f"Prepared by: {author}"), styles["subtitle"]))

    date = data.get("date", datetime.now().strftime("%B %d, %Y"))
    elements.append(Paragraph(clean_text(f"Date: {date}"), styles["subtitle"]))

    description = data.get("description")
    if description:
        elements.append(Spacer(1, 1.5 * cm))
        elements.append(Paragraph(clean_text(description), styles["body_italic"]))

    elements.append(PageBreak())
    return elements


def _build_dataset_overview(
    data: dict[str, Any], styles: dict, section: int,
) -> list:
    """Build the Dataset Overview section."""
    overview = data.get("dataset_overview")
    if not overview:
        return []

    elements: list = []
    elements.append(
        Paragraph(clean_text(f"{section}. Dataset Overview"), styles["section_heading"])
    )
    elements.append(_section_divider())

    # KPI cards row
    rows_val = str(overview.get("rows", "–"))
    cols_val = str(overview.get("columns", "–"))
    fname = overview.get("filename", "N/A")
    fsize = overview.get("file_size", "N/A")

    elements.append(_kpi_row([
        (rows_val, "Rows"),
        (cols_val, "Columns"),
        (str(fsize), "File Size"),
    ], styles))
    elements.append(Spacer(1, 0.4 * cm))

    elements.append(
        Paragraph(clean_text(f"<b>File Name:</b> {fname}"), styles["body_bold"])
    )

    # Column listing
    col_list = overview.get("column_names")
    if col_list:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph(clean_text("Columns:"), styles["sub_heading"]))
        for col in col_list:
            elements.append(Paragraph(clean_text(f"• {col}"), styles["bullet"]))

    # Data types table
    dtypes = overview.get("dtypes")
    if dtypes:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph(clean_text("Data Types:"), styles["sub_heading"]))
        tbl_rows = [[col, dtype] for col, dtype in dtypes.items()]
        elements.append(_build_table(["Column", "Type"], tbl_rows))

    elements.append(Spacer(1, 0.5 * cm))
    return elements


def _build_eda_section(
    data: dict[str, Any], styles: dict, section: int,
) -> list:
    """Build the EDA Statistics & Key Findings section."""
    eda = data.get("eda_summary")
    if not eda:
        return []

    elements: list = []
    elements.append(
        Paragraph(clean_text(f"{section}. Exploratory Data Analysis"), styles["section_heading"])
    )
    elements.append(_section_divider())

    # — Descriptive statistics
    desc_stats = eda.get("descriptive_stats")
    if desc_stats:
        elements.append(
            Paragraph(clean_text("Descriptive Statistics"), styles["sub_heading"])
        )

        numeric_cols = {
            col: stats for col, stats in desc_stats.items() if "mean" in stats
        }
        if numeric_cols:
            headers = ["Column", "Count", "Mean", "Std", "Min", "Max"]
            rows = []
            for col, st in numeric_cols.items():
                rows.append([
                    col,
                    str(_fmt(st.get("count"))),
                    str(_fmt(st.get("mean"))),
                    str(_fmt(st.get("std"))),
                    str(_fmt(st.get("min"))),
                    str(_fmt(st.get("max"))),
                ])
            elements.append(_build_table(headers, rows))
            elements.append(Spacer(1, 0.4 * cm))

        cat_cols = {
            col: stats for col, stats in desc_stats.items()
            if "unique" in stats and "mean" not in stats
        }
        if cat_cols:
            elements.append(
                Paragraph(clean_text("Categorical Summary"), styles["sub_heading"])
            )
            headers = ["Column", "Count", "Unique", "Top", "Freq"]
            rows = []
            for col, st in cat_cols.items():
                rows.append([
                    col,
                    str(_fmt(st.get("count"))),
                    str(_fmt(st.get("unique"))),
                    str(st.get("top", "N/A")),
                    str(_fmt(st.get("freq"))),
                ])
            elements.append(_build_table(headers, rows))
            elements.append(Spacer(1, 0.4 * cm))

    # — Missing values
    mv = eda.get("missing_values")
    if mv:
        elements.append(Paragraph(clean_text("Missing Values"), styles["sub_heading"]))
        total = mv.get("total_missing", 0)
        elements.append(
            Paragraph(clean_text(f"Total missing cells: <b>{total}</b>"), styles["body_bold"])
        )
        cols_mv = mv.get("columns", {})
        affected = {
            c: info for c, info in cols_mv.items() if info.get("count", 0) > 0
        }
        if affected:
            headers = ["Column", "Missing Count", "Percentage"]
            rows = [
                [col, str(info["count"]), f"{info['percentage']}%"]
                for col, info in affected.items()
            ]
            elements.append(_build_table(headers, rows))
        else:
            elements.append(
                Paragraph(clean_text("No missing values detected."), styles["body"])
            )
        elements.append(Spacer(1, 0.4 * cm))

    # — Outliers
    outliers = eda.get("outliers")
    if outliers:
        elements.append(
            Paragraph(clean_text("Outlier Detection (IQR)"), styles["sub_heading"])
        )
        total_rows = outliers.get("total_outlier_rows", 0)
        elements.append(
            Paragraph(
                clean_text(f"Rows with at least one outlier: <b>{total_rows}</b>"),
                styles["body_bold"],
            )
        )
        cols_out = outliers.get("columns", {})
        affected_out = {
            c: info for c, info in cols_out.items()
            if info.get("outlier_count", 0) > 0
        }
        if affected_out:
            headers = ["Column", "Outliers", "Lower Bound", "Upper Bound"]
            rows = [
                [
                    col,
                    str(info["outlier_count"]),
                    str(_fmt(info.get("lower_bound"))),
                    str(_fmt(info.get("upper_bound"))),
                ]
                for col, info in affected_out.items()
            ]
            elements.append(_build_table(headers, rows))
        elements.append(Spacer(1, 0.4 * cm))

    # — Key findings
    findings = eda.get("key_findings")
    if findings:
        elements.append(Paragraph(clean_text("Key Findings"), styles["sub_heading"]))
        for finding in findings:
            elements.append(Paragraph(clean_text(f"• {finding}"), styles["bullet"]))
        elements.append(Spacer(1, 0.3 * cm))

    return elements


def _build_ai_insights(
    data: dict[str, Any], styles: dict, section: int,
) -> list:
    """Build the AI-Generated Narrative Insights section (§3).

    Calls Ollama to generate 3-4 sentences of plain English insights
    about the dataset based on the EDA summary.
    """
    eda = data.get("eda_summary")
    if not eda:
        return []

    elements: list = []
    elements.append(
        Paragraph(
            clean_text(f"{section}. AI-Generated Narrative Insights"),
            styles["section_heading"],
        )
    )
    elements.append(_section_divider())

    # Check for pre-provided insights or generate via Ollama
    ai_insights = data.get("ai_insights")
    if not ai_insights:
        prompt = _build_insights_prompt(eda)
        ai_insights = _generate_ai_text(
            prompt,
            model=data.get("ollama_model", "mistral"),
            host=data.get("ollama_host", "http://localhost:11434"),
            backend=data.get("llm_backend", "ollama"),
            api_key=data.get("gemini_api_key"),
        )

    if ai_insights:
        paragraphs = ai_insights.strip().split("\n\n")
        for para in paragraphs:
            clean = para.strip().replace("\n", " ")
            if clean:
                elements.append(Paragraph(clean_text(clean), styles["callout"]))
    else:
        elements.append(
            Paragraph(
                clean_text("<i>AI insights could not be generated. Ensure Ollama is "
                "running locally with a model available.</i>"),
                styles["body_italic"],
            )
        )

    elements.append(Spacer(1, 0.5 * cm))
    return elements


# Old clean_text removed, now at top block


def _render_matplotlib_charts(df, styles: dict) -> list:
    """Render top 3 charts using matplotlib/seaborn and return as a list of Flowables."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from reportlab.platypus import Image, KeepTogether, Spacer
    from reportlab.lib.units import cm
    from reportlab.lib.pagesizes import A4
    
    page_w = A4[0]
    def title_case(s): return str(s).replace('_', ' ').title()
    
    elements = []
    
    # Chart 1: Bar chart of top categorical column
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    if cat_cols:
        top_cat = df[cat_cols].nunique().idxmax()
        counts = df[top_cat].value_counts().nlargest(10)
        
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.barplot(x=counts.values, y=counts.index, ax=ax, palette="viridis")
        ax.set_title(f"Top 10 Values in {top_cat}", pad=14)
        ax.set_xlabel("Count")
        fig.tight_layout()
        
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        plt.close(fig)
        buf.seek(0)
        
        heading = Paragraph(clean_text(f"{title_case(top_cat)} Distribution"), styles["sub_heading"])
        img = Image(buf)
        img_w = page_w - 5 * cm
        img.drawWidth = img_w
        img.drawHeight = img_w * 0.66
        elements.append(KeepTogether([heading, img]))
        elements.append(Spacer(1, 0.5 * cm))

    # Chart 2: Histogram of most important numeric column
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        top_num = df[num_cols].var().idxmax()
        
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.histplot(df[top_num], kde=True, ax=ax, color='#2E86C1')
        ax.set_title(f"Distribution of {top_num}", pad=14)
        fig.tight_layout()
        
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        plt.close(fig)
        buf.seek(0)
        
        heading = Paragraph(clean_text(f"{title_case(top_num)} Histogram"), styles["sub_heading"])
        img = Image(buf)
        img_w = page_w - 5 * cm
        img.drawWidth = img_w
        img.drawHeight = img_w * 0.66
        elements.append(KeepTogether([heading, img]))
        elements.append(Spacer(1, 0.5 * cm))

    # Chart 3: Correlation heatmap using Seaborn
    if len(num_cols) >= 2:
        corr = df[num_cols].corr()
        
        fig, ax = plt.subplots(figsize=(6, 5))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", cbar=True, ax=ax, 
                    annot_kws={"size": 8})
        ax.set_title("Numeric Correlation Heatmap", pad=14)
        fig.tight_layout()
        
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        plt.close(fig)
        buf.seek(0)
        
        heading = Paragraph(clean_text("Correlation Heatmap"), styles["sub_heading"])
        img = Image(buf)
        img_w = page_w - 5 * cm
        img.drawWidth = img_w
        img.drawHeight = img_w * 0.83
        elements.append(KeepTogether([heading, img]))
        elements.append(Spacer(1, 0.5 * cm))
        
    return elements


def _build_data_insights(
    data: dict[str, Any], styles: dict, section: int,
) -> list:
    """Build the new Data Insights Dashboard section."""
    try:
        import streamlit as st
    except ImportError:
        return []

    exec_summary = st.session_state.get('viz_executive_summary', '')
    kpis = st.session_state.get('viz_kpis', {})
    insights = st.session_state.get('viz_insights', '')

    if not any([exec_summary, kpis, insights]):
        return []

    elements: list = []
    elements.append(
        Paragraph(clean_text(f"{section}. Data Insights Dashboard"), styles["section_heading"])
    )
    elements.append(_section_divider())

    if exec_summary:
        elements.append(Paragraph(clean_text("Executive Summary"), styles["sub_heading"]))
        elements.append(Paragraph(clean_text(exec_summary), styles["body"]))
        elements.append(Spacer(1, 0.4 * cm))

    if kpis:
        elements.append(Paragraph(clean_text("Business KPIs"), styles["sub_heading"]))
        pairs = []
        if isinstance(kpis, dict):
            for k, v in kpis.items():
                pairs.append((str(v), str(k)))
        elif isinstance(kpis, list):
            for idx, item in enumerate(kpis):
                if isinstance(item, dict):
                    name = str(item.get("name", f"KPI {idx+1}"))
                    val = str(item.get("value", ""))
                    pairs.append((val, name))
                else:
                    pairs.append((str(item), f"KPI {idx+1}"))
        
        if pairs:
            for i in range(0, len(pairs), 4):
                elements.append(_kpi_row(pairs[i:i+4], styles))
            elements.append(Spacer(1, 0.4 * cm))

    if insights:
        elements.append(Paragraph(clean_text("AI Business Insights"), styles["sub_heading"]))
        cleaned_insights = clean_text(insights)
        paragraphs = cleaned_insights.split("\n")
        for para in paragraphs:
            if para:
                cleaned = clean_text(para)
                if cleaned:
                    try:
                        elements.append(Paragraph(cleaned, styles["bullet"] if para.strip().startswith("•") else styles["body"]))
                    except Exception:
                        elements.append(Paragraph(cleaned.encode('ascii', 'ignore').decode(), styles["body"]))
        elements.append(Spacer(1, 0.5 * cm))

    # Generate the 3 charts here natively with Matplotlib
    if "df" in st.session_state:
        df = st.session_state["df"]
        elements.extend(_render_matplotlib_charts(df, styles))

    return elements


def _build_visualizations(
    data: dict[str, Any], styles: dict, section: int,
) -> list:
    """Build the Visualizations section with embedded charts."""
    eda = data.get("eda_summary")
    
    dist_bytes = _render_distribution_chart(eda) if eda else None

    if not dist_bytes:
        return []

    elements: list = []
    from reportlab.platypus import PageBreak
    elements.append(PageBreak())
    elements.append(
        Paragraph(clean_text(f"{section}. Visualizations"), styles["section_heading"])
    )
    elements.append(_section_divider())

    if dist_bytes:
        heading = Paragraph(clean_text("Numeric Column Distributions"), styles["sub_heading"])
        img = Image(io.BytesIO(dist_bytes))
        img_w = _PAGE_W - 5 * cm
        img.drawWidth = img_w
        img.drawHeight = img_w * 0.58
        elements.append(KeepTogether([heading, img]))
        elements.append(Spacer(1, 0.5 * cm))

    return elements


def _build_ml_section(
    data: dict[str, Any], styles: dict, section: int,
) -> list:
    """Build the ML Model Comparison section."""
    ml = data.get("ml_comparison")
    if not ml:
        return []

    elements: list = []
    elements.append(
        Paragraph(
            clean_text(f"{section}. Machine Learning Model Comparison"),
            styles["section_heading"],
        )
    )
    elements.append(_section_divider())

    task_type = ml.get("task_type", "N/A")
    target = ml.get("target_column", "N/A")
    elements.append(
        Paragraph(
            clean_text(f"<b>Task Type:</b> {task_type} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Target Column:</b> {target}"),
            styles["body_bold"],
        )
    )
    elements.append(
        Paragraph(
            clean_text(f"<b>Training Samples:</b> {ml.get('train_samples', 'N/A')} "
            f"&nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Test Samples:</b> {ml.get('test_samples', 'N/A')}"),
            styles["body_bold"],
        )
    )
    elements.append(Spacer(1, 0.3 * cm))

    results = ml.get("results", [])
    if results:
        metric_keys: list[str] = []
        for r in results:
            if r.get("metrics"):
                metric_keys = list(r["metrics"].keys())
                break

        headers = ["Rank", "Model"] + [_title_case(k) for k in metric_keys]
        rows = []
        sorted_results = sorted(results, key=lambda r: r.get("rank") or 999)
        for r in sorted_results:
            rank = r.get("rank", "–")
            model = r.get("model", "Unknown")
            metrics = r.get("metrics", {})
            row = [str(rank), model] + [
                str(_fmt(metrics.get(k))) for k in metric_keys
            ]
            rows.append(row)

        elements.append(_build_table(headers, rows))

    best = ml.get("best_model")
    if best:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(
            Paragraph(clean_text(f"<b>Best Model:</b> {best}"), styles["body_bold"])
        )

    elements.append(Spacer(1, 0.5 * cm))
    return elements


def _build_ai_summary(
    data: dict[str, Any], styles: dict, section: int,
) -> list:
    """Build the AI-Generated Summary section."""
    summary = data.get("ai_summary")
    if not summary:
        return []

    elements: list = []
    elements.append(
        Paragraph(clean_text(f"{section}. AI-Generated Summary"), styles["section_heading"])
    )
    elements.append(_section_divider())

    paragraphs = summary.strip().split("\n\n")
    for para in paragraphs:
        clean = para.strip().replace("\n", " ")
        if clean:
            elements.append(Paragraph(clean_text(clean), styles["body"]))

    elements.append(Spacer(1, 0.5 * cm))
    return elements


def _build_conclusion(
    data: dict[str, Any], styles: dict, section: int,
) -> list:
    """Build the AI-Generated Conclusion & Next Steps section.

    Calls Ollama to generate a 2-paragraph conclusion based on the
    analysis results gathered throughout the report.
    """
    elements: list = []
    elements.append(
        Paragraph(
            clean_text(f"{section}. Conclusion & Next Steps"),
            styles["section_heading"],
        )
    )
    elements.append(_section_divider())

    # Check for pre-provided conclusion or generate via Ollama
    conclusion = data.get("conclusion")
    if not conclusion:
        prompt = _build_conclusion_prompt(data)
        conclusion = _generate_ai_text(
            prompt,
            model=data.get("ollama_model", "mistral"),
            host=data.get("ollama_host", "http://localhost:11434"),
            backend=data.get("llm_backend", "ollama"),
            api_key=data.get("gemini_api_key"),
            max_tokens=500,
        )

    if conclusion:
        # Strip labels like "Paragraph 1:", "Summary:", "Next Steps:" etc.
        import re as _re
        conclusion = _re.sub(
            r"^(?:Paragraph\s*\d\s*[:\-–—]|Summary\s*[:\-–—]|"
            r"Next\s*Steps?\s*[:\-–—]|Conclusion\s*[:\-–—])\s*",
            "",
            conclusion,
            flags=_re.MULTILINE | _re.IGNORECASE,
        )
        paragraphs = conclusion.strip().split("\n\n")
        for para in paragraphs:
            clean = para.strip().replace("\n", " ")
            if clean:
                elements.append(Paragraph(clean_text(clean), styles["body"]))
    else:
        elements.append(
            Paragraph(
                clean_text("<i>Conclusion could not be generated automatically. "
                "Ensure Ollama is running locally with a model available.</i>"),
                styles["body_italic"],
            )
        )

    elements.append(Spacer(1, 0.5 * cm))
    return elements


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fmt(value: Any) -> str:
    """Format a value for display in the report."""
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.4f}" if abs(value) < 1 else f"{value:,.2f}"
    return str(value)


def _title_case(snake: str) -> str:
    """Convert ``'f1_score'`` → ``'F1 Score'``."""
    return snake.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Page decorators (header / footer)
# ---------------------------------------------------------------------------
def _add_page_number(canvas, doc):
    """Add a polished footer with page number and header line."""
    canvas.saveState()

    # Header accent line
    canvas.setStrokeColor(_ACCENT_LIGHT)
    canvas.setLineWidth(0.8)
    canvas.line(2 * cm, _PAGE_H - 2 * cm, _PAGE_W - 2 * cm, _PAGE_H - 2 * cm)

    # Footer line
    canvas.setStrokeColor(colors.HexColor("#e0e0e0"))
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 2 * cm, _PAGE_W - 2 * cm, 2 * cm)

    # Page number
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_MUTED)
    page_num = canvas.getPageNumber()
    canvas.drawCentredString(_PAGE_W / 2, 1.5 * cm, f"Page {page_num}")

    # Right-side branding
    canvas.setFont("Helvetica-Oblique", 7)
    canvas.drawRightString(
        _PAGE_W - 2 * cm, 1.5 * cm, "AI Data Platform"
    )

    canvas.restoreState()


def _add_title_page_footer(canvas, doc):
    """Minimal footer for the title page (no page number)."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_MUTED)
    canvas.drawCentredString(
        _PAGE_W / 2, 1.5 * cm, "Generated by AI Data Platform"
    )
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_report(
    data: dict[str, Any],
    output_path: str | Path = "report.pdf",
) -> str:
    """Generate a professional PDF report from *data*.

    Parameters
    ----------
    data : dict[str, Any]
        Report content dictionary. Expected keys (all optional except title):

        - ``title`` : str – report title (default "Data Analysis Report").
        - ``author`` : str – preparer name.
        - ``date`` : str – report date.
        - ``description`` : str – short intro paragraph.
        - ``dataset_overview`` : dict – output of ``data_loader`` summary.
        - ``eda_summary`` : dict – output of ``eda.run_eda``.
        - ``ai_insights`` : str | None – pre-provided narrative insights
          (if ``None``, calls Ollama to generate).
        - ``ml_comparison`` : dict – output of ``ml_engine.run_ml``.
        - ``ai_summary`` : str – LLM-generated narrative.
        - ``conclusion`` : str | None – pre-provided conclusion text
          (if ``None``, calls Ollama to generate).
        - ``ollama_model`` : str – Ollama model tag (default ``"mistral"``).
        - ``ollama_host`` : str – Ollama server URL.

    output_path : str | Path
        Destination file path (default ``"report.pdf"``).

    Returns
    -------
    str
        Absolute path of the generated PDF file.

    Raises
    ------
    ValueError
        If *data* is ``None`` or not a dict.
    """
    if data is None or not isinstance(data, dict):
        raise ValueError(f"Expected a dict, got {type(data).__name__}.")

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Generating report → %s", output_path)

    styles = _get_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=data.get("title", "Data Analysis Report"),
        author=data.get("author", "AI Data Platform"),
    )

    elements: list = []
    sec = 1  # auto-incrementing section counter

    # Title page (unnumbered)
    elements.extend(_build_title_page(data, styles))

    # §1 Dataset overview
    section_elems = _build_dataset_overview(data, styles, sec)
    if section_elems:
        elements.extend(section_elems)
        sec += 1

    # §2 EDA
    section_elems = _build_eda_section(data, styles, sec)
    if section_elems:
        elements.extend(section_elems)
        sec += 1

    # §3 AI Narrative Insights (NEW)
    section_elems = _build_ai_insights(data, styles, sec)
    if section_elems:
        elements.extend(section_elems)
        sec += 1

    # §4 Data Insights Dashboard (NEW)
    section_elems = _build_data_insights(data, styles, sec)
    if section_elems:
        elements.extend(section_elems)
        sec += 1

    # §5 Visualizations
    section_elems = _build_visualizations(data, styles, sec)
    if section_elems:
        elements.extend(section_elems)
        sec += 1

    # §6 ML comparison
    section_elems = _build_ml_section(data, styles, sec)
    if section_elems:
        elements.extend(section_elems)
        sec += 1

    # §7 AI summary
    section_elems = _build_ai_summary(data, styles, sec)
    if section_elems:
        elements.extend(section_elems)
        sec += 1

    # §8 Conclusion & Next Steps
    has_analysis = (
        data.get("eda_summary")
        or data.get("ml_comparison")
        or data.get("ai_summary")
    )
    if has_analysis or data.get("conclusion"):
        elements.extend(_build_conclusion(data, styles, sec))

    # Build the PDF
    doc.build(
        elements,
        onFirstPage=_add_title_page_footer,
        onLaterPages=_add_page_number,
    )

    logger.info("Report generated: %s", output_path)
    return str(output_path)
