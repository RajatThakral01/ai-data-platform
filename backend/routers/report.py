from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from session_store import get_session
import pandas as pd
from fpdf import FPDF

def safe_text(text):
    """Convert text to latin-1 to remove unsupported Unicode characters."""
    return str(text).encode('latin-1', errors='replace').decode('latin-1')

router = APIRouter()


@router.post("/report")
async def generate_report(body: dict):
    session_id = body.get("session_id")
    session = get_session(session_id)
    if not session or "df" not in session:
        raise HTTPException(status_code=404,
            detail="Session not found")

    df = session["df"]
    if isinstance(df, dict):
        df = pd.DataFrame(df)

    filename = session.get("filename", "dataset")
    eda_results = session.get("eda_results")
    ml_results = session.get("ml_results")
    insights_results = session.get("insights_results")
    cleaned_df_data = session.get("cleaned_df")
    if isinstance(cleaned_df_data, list):
        cleaned_df = pd.DataFrame(cleaned_df_data)
    elif isinstance(cleaned_df_data, dict):
        cleaned_df = pd.DataFrame(cleaned_df_data)
    else:
        cleaned_df = cleaned_df_data

    print(f"Report session keys: {list(session.keys())}")
    print(f"EDA results: {'YES' if eda_results else 'NO'}")
    print(f"ML results: {'YES' if ml_results else 'NO'}")
    print(f"Insights: {'YES' if insights_results else 'NO'}")
    print(f"Cleaned df: {'YES' if cleaned_df_data else 'NO'}")

    # -- helpers --
    def section(color, title, body_html):
        return f"""
        <div class="section">
          <div class="section-header" 
               style="background:{color}">
            {title}
          </div>
          <div class="section-body">{body_html}</div>
        </div>"""

    def safe_table(df_or_html):
        if isinstance(df_or_html, pd.DataFrame):
            return df_or_html.to_html(
                border=0, classes="table",
                na_rep="--")
        return df_or_html

    # -- SECTION 1: Overview --
    col_rows = "".join(
        f"<tr><td>{c}</td>"
        f"<td>{str(df[c].dtype)}</td>"
        f"<td>{df[c].nunique():,}</td></tr>"
        for c in df.columns
    )
    s1 = f"""
    <div class="meta">
      <p><strong>Dataset:</strong> {filename}</p>
      <p><strong>Rows:</strong> {len(df):,}</p>
      <p><strong>Columns:</strong> {len(df.columns)}</p>
      <p><strong>Generated:</strong> 
         {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
      </p>
    </div>
    <table class="table">
      <tr><th>Column</th><th>Type</th>
          <th>Unique Values</th></tr>
      {col_rows}
    </table>"""

    # -- SECTION 2: Data Quality --
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    total_missing = df.isnull().sum().sum()
    dupes = df.duplicated().sum()
    missing_table = (
        missing.to_frame("Missing Count")
        .to_html(border=0, classes="table")
        if len(missing) > 0
        else "<p>No missing values.</p>"
    )
    s2 = f"""
    <div class="stats-row">
      <div class="stat-box">
        <div class="stat-num">{total_missing:,}</div>
        <div class="stat-label">Total Missing Cells</div>
      </div>
      <div class="stat-box">
        <div class="stat-num">{dupes:,}</div>
        <div class="stat-label">Duplicate Rows</div>
      </div>
      <div class="stat-box">
        <div class="stat-num">
          {total_missing / df.size * 100:.1f}%
        </div>
        <div class="stat-label">Missing Rate</div>
      </div>
    </div>
    {missing_table}"""

    # -- SECTION 3: Statistics --
    stats_html = df.describe().round(2).to_html(
        border=0, classes="table", na_rep="--")

    cat_cols = df.select_dtypes(
        include=["object", "category"]).columns
    cat_html = ""
    for col in cat_cols[:5]:
        vc = df[col].value_counts().head(5)
        cat_html += f"<h4>{col}</h4>"
        cat_html += vc.to_frame(
            "Count").to_html(border=0, classes="table")

    s3 = f"{stats_html}{cat_html}"

    # -- SECTION 4: EDA --
    s4 = ""
    if eda_results:
        narrative = eda_results.get("narrative", "")
        outliers = eda_results.get("outliers", {})
        outlier_rows = "".join(
            f"<tr><td>{k}</td><td>{v}</td></tr>"
            for k, v in outliers.items() if v > 0
        )
        s4 = f"""
        <div class="narrative">{narrative}</div>
        {"<h4>Outliers Detected</h4><table class='table'>"
         "<tr><th>Column</th><th>Count</th></tr>"
         + outlier_rows + "</table>"
         if outlier_rows else ""}"""

    # -- SECTION 5: Cleaning --
    s5 = ""
    if cleaned_df is not None:
        before_missing = df.isnull().sum().sum()
        after_missing = cleaned_df.isnull().sum().sum()
        s5 = f"""
        <table class="table">
          <tr><th></th><th>Before</th><th>After</th></tr>
          <tr><td>Rows</td>
              <td>{len(df):,}</td>
              <td>{len(cleaned_df):,}</td></tr>
          <tr><td>Missing Values</td>
              <td>{before_missing:,}</td>
              <td>{after_missing:,}</td></tr>
        </table>"""

    # -- SECTION 6: ML Results --
    s6 = ""
    if ml_results:
        task = ml_results.get("task_type", "")
        best = ml_results.get("best_model", "")
        models = ml_results.get("models", [])
        model_rows = "".join(
            f"<tr {'style=background:#fff3cd' if m.get('name')==best else ''}>"
            f"<td>{m.get('name','')}</td>"
            f"<td>{m.get('score',0):.4f}</td>"
            f"<td>{m.get('training_time_ms',0)}ms</td></tr>"
            for m in models
        )
        summary = ml_results.get("ai_summary", "")
        s6 = f"""
        <p><strong>Task Type:</strong> {task}</p>
        <p><strong>Best Model:</strong> 
           <span style="color:#c0392b;font-weight:bold">
           {best}</span></p>
        <table class="table">
          <tr><th>Model</th><th>Score</th><th>Time</th></tr>
          {model_rows}
        </table>
        <div class="narrative">{summary}</div>"""

    # -- SECTION 7: Insights --
    s7 = ""
    if insights_results:
        summary = insights_results.get(
            "executive_summary", "")
        kpis = insights_results.get("kpis", [])
        insights = insights_results.get("ai_insights", [])
        kpi_rows = "".join(
            f"<tr><td>{k.get('label','')}</td>"
            f"<td><strong>"
            f"{k.get('formatted_value','')}"
            f"</strong></td></tr>"
            for k in kpis
        )
        insight_items = "".join(
            f"<li>{i}</li>" for i in insights
        )
        s7 = f"""
        <div class="narrative">{summary}</div>
        {"<table class='table'><tr><th>KPI</th>"
         "<th>Value</th></tr>" + kpi_rows + "</table>"
         if kpi_rows else ""}
        {"<ul>" + insight_items + "</ul>" 
         if insight_items else ""}"""

    # -- ASSEMBLE HTML --
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page {{ margin: 20mm; }}
  body {{ font-family: Arial, sans-serif; 
          color: #111; font-size: 13px; }}
  h1 {{ color: #0055cc; font-size: 24px; }}
  h4 {{ margin: 16px 0 4px; color: #333; }}
  .meta {{ background: #f0f7ff; 
           border-left: 4px solid #0055cc;
           padding: 12px 16px; border-radius: 4px; 
           margin: 16px 0; }}
  .meta p {{ margin: 3px 0; }}
  .section {{ margin-bottom: 32px; 
              page-break-inside: avoid; }}
  .section-header {{ color: white; padding: 8px 16px;
                     font-size: 15px; font-weight: bold;
                     border-radius: 4px 4px 0 0; }}
  .section-body {{ padding: 16px; border: 1px solid #eee;
                   border-top: none; 
                   border-radius: 0 0 4px 4px; }}
  .table {{ border-collapse: collapse; width: 100%;
            font-size: 12px; margin: 8px 0; }}
  .table th, .table td {{ border: 1px solid #ddd;
                          padding: 6px 10px; 
                          text-align: left; }}
  .table th {{ background: #f5f5f5; font-weight: bold; }}
  .table tr:nth-child(even) {{ background: #fafafa; }}
  .stats-row {{ display: flex; gap: 16px; 
                margin: 12px 0; }}
  .stat-box {{ flex: 1; text-align: center;
               padding: 12px; background: #f8f9fa;
               border-radius: 6px; 
               border: 1px solid #dee2e6; }}
  .stat-num {{ font-size: 22px; font-weight: bold;
               color: #0055cc; }}
  .stat-label {{ font-size: 11px; color: #666;
                 margin-top: 4px; }}
  .narrative {{ background: #f8f9fa; 
                border-left: 3px solid #0055cc;
                padding: 12px; border-radius: 0 4px 4px 0;
                font-style: italic; margin: 12px 0; }}
  .footer {{ text-align: center; color: #999; 
             font-size: 11px; margin-top: 40px;
             border-top: 1px solid #eee; 
             padding-top: 12px; }}
  .toc {{ background: #f8f9fa; padding: 16px;
          border-radius: 4px; margin-bottom: 24px; }}
  .toc a {{ color: #0055cc; text-decoration: none;
            display: block; margin: 4px 0; }}
</style>
</head><body>

<h1>AI Data Analysis Report</h1>

<div class="toc">
  <strong>Contents</strong><br>
  <a href="#s1">1. Dataset Overview</a>
  <a href="#s2">2. Data Quality</a>
  <a href="#s3">3. Descriptive Statistics</a>
  {"<a href='#s4'>4. EDA Results</a>" 
   if eda_results else ""}
  {"<a href='#s5'>5. Data Cleaning</a>" 
   if cleaned_df is not None else ""}
  {"<a href='#s6'>6. ML Results</a>" 
   if ml_results else ""}
  {"<a href='#s7'>7. Business Insights</a>" 
   if insights_results else ""}
</div>

<div id="s1">
  {section("#0055cc", "1. Dataset Overview", s1)}
</div>
<div id="s2">
  {section("#e65c00", "2. Data Quality", s2)}
</div>
<div id="s3">
  {section("#006644", "3. Descriptive Statistics", s3)}
</div>
{"<div id='s4'>" + section("#5b2d8e","4. EDA Results",s4) + "</div>" if eda_results else ""}
{"<div id='s5'>" + section("#c7960a","5. Data Cleaning",s5) + "</div>" if cleaned_df is not None else ""}
{"<div id='s6'>" + section("#c0392b","6. ML Results",s6) + "</div>" if ml_results else ""}
{"<div id='s7'>" + section("#1a7a4a","7. Business Insights",s7) + "</div>" if insights_results else ""}

<div class="footer">
  Generated by AI Data Platform &nbsp;|&nbsp; 
  {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
</div>

</body></html>"""

    # -- CONVERT TO PDF --
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(0, 85, 204)
    pdf.cell(0, 12, safe_text("AI Data Analysis Report"), ln=True)
    pdf.ln(4)

    # Meta info
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(50, 50, 50)
    pdf.set_fill_color(240, 247, 255)
    pdf.rect(15, pdf.get_y(), 180, 28, "F")
    pdf.set_x(18)
    pdf.cell(0, 7, safe_text(f"Dataset: {filename}"), ln=True)
    pdf.set_x(18)
    pdf.cell(0, 7, safe_text(f"Rows: {len(df):,}   |   Columns: {len(df.columns)}"), ln=True)
    pdf.set_x(18)
    pdf.cell(0, 7, safe_text(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"), ln=True)
    pdf.ln(6)

    def section_header(pdf, title, r, g, b):
        pdf.set_fill_color(r, g, b)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 9, safe_text(f"  {title}"), ln=True, fill=True)
        pdf.set_text_color(50, 50, 50)
        pdf.ln(2)

    def add_dataframe_table(pdf, df_table):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(245, 245, 245)
        cols = list(df_table.columns)
        col_width = 175 / max(len(cols) + 1, 2)
        # Header row
        pdf.set_x(15)
        pdf.cell(col_width, 7, safe_text("Index"), border=1, fill=True)
        for col in cols:
            pdf.cell(col_width, 7, safe_text(str(col)[:15]), border=1, fill=True)
        pdf.ln()
        # Data rows
        pdf.set_font("Helvetica", "", 8)
        for i, (idx, row) in enumerate(df_table.iterrows()):
            if pdf.get_y() > 270:
                pdf.add_page()
            fill = i % 2 == 0
            pdf.set_fill_color(250, 250, 250) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.set_x(15)
            pdf.cell(col_width, 6, safe_text(str(idx)[:15]), border=1, fill=fill)
            for val in row:
                pdf.cell(col_width, 6, safe_text(str(round(val, 2) if isinstance(val, float) else val)[:15]), border=1, fill=fill)
            pdf.ln()
        pdf.ln(4)

    # SECTION 1: Overview
    section_header(pdf, "1. Dataset Overview", 0, 85, 204)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_x(15)
    pdf.cell(80, 7, safe_text("Column"), border=1, fill=True)
    pdf.cell(50, 7, safe_text("Type"), border=1, fill=True)
    pdf.cell(45, 7, safe_text("Unique Values"), border=1, fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for i, col in enumerate(df.columns):
        fill = i % 2 == 0
        pdf.set_fill_color(250, 250, 250) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_x(15)
        pdf.cell(80, 6, safe_text(str(col)[:35]), border=1, fill=fill)
        pdf.cell(50, 6, safe_text(str(df[col].dtype)), border=1, fill=fill)
        pdf.cell(45, 6, safe_text(str(df[col].nunique())), border=1, fill=fill)
        pdf.ln()
    pdf.ln(6)

    # SECTION 2: Data Quality
    section_header(pdf, "2. Data Quality", 230, 92, 0)
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    total_missing = df.isnull().sum().sum()
    dupes = df.duplicated().sum()
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, safe_text(f"Total Missing Cells: {total_missing:,}   |   Missing Rate: {total_missing/df.size*100:.1f}%   |   Duplicate Rows: {dupes:,}"), ln=True)
    pdf.ln(2)
    if len(missing) > 0:
        add_dataframe_table(pdf, missing.to_frame("Missing Count"))
    else:
        pdf.cell(0, 7, safe_text("No missing values found."), ln=True)
    pdf.ln(4)

    # SECTION 3: Statistics
    section_header(pdf, "3. Descriptive Statistics", 0, 102, 68)
    add_dataframe_table(pdf, df.describe().round(2))

    # SECTION 4: EDA (if available)
    if eda_results:
        pdf.add_page()
        section_header(pdf, "4. EDA Results", 91, 45, 142)
        narrative = eda_results.get("narrative", "")
        if narrative:
            pdf.set_font("Helvetica", "I", 9)
            pdf.multi_cell(180, 5, safe_text(narrative[:800]))
            pdf.ln(4)

    # SECTION 5: Cleaning (if available)
    if cleaned_df is not None:
        section_header(pdf, "5. Data Cleaning Summary", 199, 149, 10)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, safe_text(f"Rows before: {len(df):,}  ->  After: {len(cleaned_df):,}"), ln=True)
        pdf.cell(0, 7, safe_text(f"Missing before: {df.isnull().sum().sum():,}  ->  After: {cleaned_df.isnull().sum().sum():,}"), ln=True)
        pdf.ln(4)

    # SECTION 6: ML Results (if available)
    if ml_results:
        section_header(pdf, "6. ML Results", 192, 57, 43)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, safe_text(f"Task Type: {ml_results.get('task_type', '')}"), ln=True)
        pdf.cell(0, 7, safe_text(f"Best Model: {ml_results.get('best_model', '')}"), ln=True)
        pdf.ln(2)
        models = ml_results.get("models", [])
        if models:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(245, 245, 245)
            pdf.set_x(15)
            pdf.cell(90, 7, safe_text("Model"), border=1, fill=True)
            pdf.cell(50, 7, safe_text("Score"), border=1, fill=True)
            pdf.cell(45, 7, safe_text("Time (ms)"), border=1, fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 9)
            for i, m in enumerate(models):
                fill = i % 2 == 0
                pdf.set_fill_color(250, 250, 250) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.set_x(15)
                pdf.cell(90, 6, safe_text(str(m.get("name", ""))[:40]), border=1, fill=fill)
                pdf.cell(50, 6, safe_text(str(round(m.get("score", 0), 4))), border=1, fill=fill)
                pdf.cell(45, 6, safe_text(str(m.get("training_time_ms", ""))), border=1, fill=fill)
                pdf.ln()
        pdf.ln(4)

    # SECTION 7: Business Insights (if available)
    if insights_results:
        section_header(pdf, "7. Business Insights", 26, 122, 74)
        summary = insights_results.get("executive_summary", "")
        if summary:
            pdf.set_font("Helvetica", "I", 9)
            pdf.multi_cell(180, 5, safe_text(summary[:800]))
            pdf.ln(4)
        insights_list = insights_results.get("ai_insights", [])
        if insights_list:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 7, safe_text("Key Insights:"), ln=True)
            pdf.set_font("Helvetica", "", 9)
            for insight in insights_list[:5]:
                pdf.multi_cell(180, 5, safe_text(f"- {str(insight)[:120]}"))
            pdf.ln(2)

    # Footer
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, safe_text("Generated by AI Data Platform"), align="C", ln=True)

    pdf_bytes = bytes(pdf.output())

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="report_{filename}.pdf"'
        }
    )
