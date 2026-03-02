"""
report_gen.py – Professional PDF report generator for the AI Data Platform.

Uses ReportLab to produce a multi-section PDF report from a single input
dictionary.  Designed to consume the outputs of ``data_loader``, ``eda``,
``ml_engine``, and ``llm`` modules directly.

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

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette (professional blue theme)
# ---------------------------------------------------------------------------
_PRIMARY = colors.HexColor("#1a237e")       # deep indigo
_SECONDARY = colors.HexColor("#283593")     # slightly lighter
_ACCENT = colors.HexColor("#3f51b5")        # indigo
_LIGHT_BG = colors.HexColor("#e8eaf6")      # very light indigo
_TABLE_HEADER = colors.HexColor("#1a237e")  # deep indigo
_TABLE_HEADER_TEXT = colors.white
_TABLE_ALT_ROW = colors.HexColor("#f5f5f5")
_TEXT = colors.HexColor("#212121")
_MUTED = colors.HexColor("#757575")

# ---------------------------------------------------------------------------
# Custom styles
# ---------------------------------------------------------------------------
_styles = getSampleStyleSheet()


def _get_styles() -> dict[str, ParagraphStyle]:
    """Return a dict of custom ParagraphStyles for the report."""
    return {
        "report_title": ParagraphStyle(
            "ReportTitle",
            parent=_styles["Title"],
            fontSize=28,
            leading=34,
            textColor=_PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=_styles["Normal"],
            fontSize=14,
            leading=18,
            textColor=_MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading",
            parent=_styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=_PRIMARY,
            spaceBefore=20,
            spaceAfter=10,
            borderWidth=1,
            borderColor=_ACCENT,
            borderPadding=(0, 0, 4, 0),
        ),
        "sub_heading": ParagraphStyle(
            "SubHeading",
            parent=_styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=_SECONDARY,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=_styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=_TEXT,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            parent=_styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=_TEXT,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=_styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=_TEXT,
            leftIndent=20,
            spaceAfter=3,
            bulletIndent=8,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=_styles["Normal"],
            fontSize=8,
            textColor=_MUTED,
            alignment=TA_CENTER,
        ),
    }


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
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), _TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), _TABLE_HEADER_TEXT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        # Body rows
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]

    # Alternate row shading
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(
                ("BACKGROUND", (0, i), (-1, i), _TABLE_ALT_ROW)
            )

    table.setStyle(TableStyle(style_cmds))
    return table


# ---------------------------------------------------------------------------
# Section builders – each returns a list of Flowable objects
# ---------------------------------------------------------------------------
def _build_title_page(data: dict[str, Any], styles: dict) -> list:
    """Build the title page."""
    elements: list = []
    elements.append(Spacer(1, 5 * cm))

    title = data.get("title", "Data Analysis Report")
    elements.append(Paragraph(title, styles["report_title"]))

    author = data.get("author", "AI Data Platform")
    elements.append(Paragraph(f"Prepared by: {author}", styles["subtitle"]))

    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    elements.append(Paragraph(f"Date: {date}", styles["subtitle"]))

    description = data.get("description")
    if description:
        elements.append(Spacer(1, 1.5 * cm))
        elements.append(Paragraph(description, styles["body"]))

    elements.append(PageBreak())
    return elements


def _build_dataset_overview(data: dict[str, Any], styles: dict) -> list:
    """Build the Dataset Overview section."""
    overview = data.get("dataset_overview")
    if not overview:
        return []

    elements: list = []
    elements.append(Paragraph("1. Dataset Overview", styles["section_heading"]))

    # Key-value pairs
    kv_items = [
        ("File Name", overview.get("filename", "N/A")),
        ("Rows", overview.get("rows", "N/A")),
        ("Columns", overview.get("columns", "N/A")),
        ("File Size", overview.get("file_size", "N/A")),
    ]
    for label, value in kv_items:
        elements.append(
            Paragraph(f"<b>{label}:</b> {value}", styles["body_bold"])
        )

    # Column listing
    col_list = overview.get("column_names")
    if col_list:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph("Columns:", styles["sub_heading"]))
        for col in col_list:
            elements.append(
                Paragraph(f"• {col}", styles["bullet"])
            )

    # Data types table
    dtypes = overview.get("dtypes")
    if dtypes:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph("Data Types:", styles["sub_heading"]))
        rows = [[col, dtype] for col, dtype in dtypes.items()]
        table = _build_table(["Column", "Type"], rows)
        elements.append(table)

    elements.append(Spacer(1, 0.5 * cm))
    return elements


def _build_eda_section(data: dict[str, Any], styles: dict) -> list:
    """Build the EDA Statistics & Key Findings section."""
    eda = data.get("eda_summary")
    if not eda:
        return []

    elements: list = []
    elements.append(
        Paragraph("2. Exploratory Data Analysis", styles["section_heading"])
    )

    # — Descriptive statistics ------------------------------------------------
    desc_stats = eda.get("descriptive_stats")
    if desc_stats:
        elements.append(
            Paragraph("Descriptive Statistics", styles["sub_heading"])
        )

        # Build one table per column type (numeric)
        numeric_cols = {
            col: stats
            for col, stats in desc_stats.items()
            if "mean" in stats
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

        # Categorical summary
        cat_cols = {
            col: stats
            for col, stats in desc_stats.items()
            if "unique" in stats and "mean" not in stats
        }
        if cat_cols:
            elements.append(
                Paragraph("Categorical Summary", styles["sub_heading"])
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

    # — Missing values --------------------------------------------------------
    mv = eda.get("missing_values")
    if mv:
        elements.append(Paragraph("Missing Values", styles["sub_heading"]))
        total = mv.get("total_missing", 0)
        elements.append(
            Paragraph(
                f"Total missing cells: <b>{total}</b>",
                styles["body_bold"],
            )
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
                Paragraph("No missing values detected.", styles["body"])
            )
        elements.append(Spacer(1, 0.4 * cm))

    # — Outliers -------------------------------------------------------------
    outliers = eda.get("outliers")
    if outliers:
        elements.append(Paragraph("Outlier Detection (IQR)", styles["sub_heading"]))
        total_rows = outliers.get("total_outlier_rows", 0)
        elements.append(
            Paragraph(
                f"Rows with at least one outlier: <b>{total_rows}</b>",
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

    # — Key findings (free-form list) ----------------------------------------
    findings = eda.get("key_findings")
    if findings:
        elements.append(Paragraph("Key Findings", styles["sub_heading"]))
        for finding in findings:
            elements.append(Paragraph(f"• {finding}", styles["bullet"]))
        elements.append(Spacer(1, 0.3 * cm))

    return elements


def _build_ml_section(data: dict[str, Any], styles: dict) -> list:
    """Build the ML Model Comparison section."""
    ml = data.get("ml_comparison")
    if not ml:
        return []

    elements: list = []
    elements.append(
        Paragraph("3. Machine Learning Model Comparison", styles["section_heading"])
    )

    task_type = ml.get("task_type", "N/A")
    target = ml.get("target_column", "N/A")
    elements.append(
        Paragraph(
            f"<b>Task Type:</b> {task_type} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Target Column:</b> {target}",
            styles["body_bold"],
        )
    )
    elements.append(
        Paragraph(
            f"<b>Training Samples:</b> {ml.get('train_samples', 'N/A')} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Test Samples:</b> {ml.get('test_samples', 'N/A')}",
            styles["body_bold"],
        )
    )
    elements.append(Spacer(1, 0.3 * cm))

    results = ml.get("results", [])
    if results:
        # Determine metric columns from the first result with metrics
        metric_keys: list[str] = []
        for r in results:
            if r.get("metrics"):
                metric_keys = list(r["metrics"].keys())
                break

        headers = ["Rank", "Model"] + [_title_case(k) for k in metric_keys]
        rows = []
        # Sort by rank
        sorted_results = sorted(
            results, key=lambda r: r.get("rank") or 999
        )
        for r in sorted_results:
            rank = r.get("rank", "–")
            model = r.get("model", "Unknown")
            metrics = r.get("metrics", {})
            row = [str(rank), model] + [
                str(_fmt(metrics.get(k))) for k in metric_keys
            ]
            rows.append(row)

        table = _build_table(headers, rows)
        elements.append(table)

    best = ml.get("best_model")
    if best:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(
            Paragraph(
                f"🏆 <b>Best Model:</b> {best}",
                styles["body_bold"],
            )
        )

    elements.append(Spacer(1, 0.5 * cm))
    return elements


def _build_ai_summary(data: dict[str, Any], styles: dict) -> list:
    """Build the AI-Generated Summary section."""
    summary = data.get("ai_summary")
    if not summary:
        return []

    elements: list = []
    elements.append(
        Paragraph("4. AI-Generated Summary", styles["section_heading"])
    )

    # Split on double newlines for paragraph separation
    paragraphs = summary.strip().split("\n\n")
    for para in paragraphs:
        clean = para.strip().replace("\n", " ")
        if clean:
            elements.append(Paragraph(clean, styles["body"]))

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
    """Add footer with page number to each page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_MUTED)
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.drawCentredString(A4[0] / 2, 1.5 * cm, text)
    # Thin line above footer
    canvas.setStrokeColor(colors.HexColor("#e0e0e0"))
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 2 * cm, A4[0] - 2 * cm, 2 * cm)
    canvas.restoreState()


def _add_title_page_footer(canvas, doc):
    """Minimal footer for the title page (no page number)."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_MUTED)
    canvas.drawCentredString(
        A4[0] / 2, 1.5 * cm, "Generated by AI Data Platform"
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
        - ``dataset_overview`` : dict – output of ``data_loader`` summary
          plus optional extra fields (filename, file_size, column_names).
        - ``eda_summary`` : dict – output of ``eda.run_eda``.
        - ``ml_comparison`` : dict – output of ``ml_engine.run_ml``.
        - ``ai_summary`` : str – LLM-generated narrative.

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

    # 1. Title page
    elements.extend(_build_title_page(data, styles))
    # 2. Dataset overview
    elements.extend(_build_dataset_overview(data, styles))
    # 3. EDA
    elements.extend(_build_eda_section(data, styles))
    # 4. ML comparison
    elements.extend(_build_ml_section(data, styles))
    # 5. AI summary
    elements.extend(_build_ai_summary(data, styles))

    # Build the PDF
    doc.build(
        elements,
        onFirstPage=_add_title_page_footer,
        onLaterPages=_add_page_number,
    )

    logger.info("Report generated: %s", output_path)
    return str(output_path)
