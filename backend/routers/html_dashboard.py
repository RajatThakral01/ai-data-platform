from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from session_store import get_session, update_session
import httpx
import os
import json
import pandas as pd
from typing import Optional

from utils.chart_planner import build_plan

router = APIRouter()


class BIDashboardRequest(BaseModel):
    session_id: str


# ── Domain Detection ──────────────────────────────────────────────────────────

def _detect_domain(columns: list[str]) -> str:
    col_str = " ".join(c.lower() for c in columns)

    scores = {
        "telecom":  sum(1 for k in ["churn","usage","calls","data_usage","plan","subscriber","minutes","network","carrier","roaming"] if k in col_str),
        "retail":   sum(1 for k in ["sales","product","category","revenue","order","customer","discount","quantity","price","sku","inventory"] if k in col_str),
        "finance":  sum(1 for k in ["transaction","amount","balance","account","credit","debit","loan","payment","interest","tax","profit"] if k in col_str),
        "hr":       sum(1 for k in ["employee","salary","department","hire","attrition","performance","headcount","tenure","manager"] if k in col_str),
        "marketing":sum(1 for k in ["campaign","clicks","impressions","conversion","ctr","cpc","leads","funnel","engagement","traffic"] if k in col_str),
    }

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


# ── Plan Builder ──────────────────────────────────────────────────────────────

def _prepare_plan(df: pd.DataFrame, session: dict) -> dict:
    """
    Build a validated dashboard plan using chart_planner.
    Uses insights_results from session if available,
    otherwise builds from scratch using domain mapper.
    """
    insights_results = session.get("insights_results")
    eda_results      = session.get("eda_results")

    if insights_results and insights_results.get("business_context"):
        domain = insights_results["business_context"].get("domain", "general")
    else:
        domain = _detect_domain(list(df.columns))

    plan = build_plan(
        df=df,
        domain=domain,
        eda_results=eda_results,
        insights_results=insights_results,
        max_charts=6,
    )

    plan["row_count"]   = len(df)
    plan["col_count"]   = len(df.columns)
    plan["all_columns"] = list(df.columns)
    plan["sample"]      = (
        df.head(3)
        .fillna("N/A")
        .astype(str)
        .to_dict(orient="records")
    )

    return plan


# ── Prompt Builder ────────────────────────────────────────────────────────────

def _build_prompt(plan: dict, filename: str) -> str:
    """
    Build LLM prompt from a validated chart plan.
    LLM is now purely a code writer — all analytical
    decisions are already made.
    """
    import json

    domain    = plan.get("domain", "general")
    kpis      = plan.get("kpis", [])
    charts    = plan.get("charts", [])
    questions = plan.get("business_questions", [])
    summary   = plan.get("executive_summary", "")
    source    = plan.get("source", "planner")

    charts_for_prompt = []
    for i, c in enumerate(charts[:6]):
        charts_for_prompt.append({
            "id":                f"chart_{i+1}",
            "type":              c.get("chart_type", "bar"),
            "title":             c.get("title", ""),
            "business_question": c.get("business_question", ""),
            "insight_hint":      c.get("insight_hint", ""),
            "x_label":           c.get("x_col", ""),
            "y_label":           c.get("y_col", ""),
            "data":              c.get("data", [])[:20],
        })

    kpis_for_prompt = [
        {"label": k.get("label",""), "value": k.get("formatted_value","")}
        for k in kpis[:4]
    ]

    return f"""You are an expert BI dashboard developer.
Your ONLY job is to write HTML/CSS/JS code.
All analytical decisions are already made — do not change them.

DATASET: {filename}
DOMAIN: {domain}
SOURCE: This plan was {"extracted from pre-computed insights" if source == "insights" else "built by the chart planning engine"}

EXECUTIVE SUMMARY (show in dashboard header):
{summary if summary else f"AI-powered {domain} analytics dashboard for {filename}"}

BUSINESS QUESTIONS THIS DASHBOARD ANSWERS:
{json.dumps(questions, indent=2)}

KPI CARDS (use EXACTLY these values — do not change them):
{json.dumps(kpis_for_prompt, indent=2)}

CHARTS TO BUILD (use EXACTLY this data — do not add or remove charts):
{json.dumps(charts_for_prompt, indent=2)}

DATASET SAMPLE (for data table):
{json.dumps(plan.get("sample", []), indent=2)}

TOTAL ROWS: {plan.get("row_count", 0):,}
TOTAL COLUMNS: {plan.get("col_count", 0)}

---
TECHNICAL REQUIREMENTS:

CDN Libraries (include in <head>):
- Chart.js: https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
- Tailwind CSS: https://cdn.tailwindcss.com
- Google Fonts: https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600&display=swap

CSS Variables (define in :root):
  --bg-primary: #080b14
  --bg-card: #0e1220
  --bg-card-hover: #141828
  --border: #1e2540
  --accent-cyan: #00e5ff
  --accent-purple: #9d4edd
  --accent-green: #00ff87
  --accent-orange: #ff6b35
  --text-primary: #e8eaf6
  --text-muted: #5c6490

LAYOUT (build in this exact order):
1. HEADER: filename + domain badge + executive summary text
2. KPI ROW: exactly {len(kpis_for_prompt)} cards with the values above
3. CHARTS GRID: render all {len(charts_for_prompt)} charts from the plan
   - Use canvas elements with IDs exactly matching:
     {[f"chart_{i+1}" for i in range(len(charts_for_prompt))]}
   - Bar/line charts: use x as labels, y as data values
   - Donut/pie charts: use x as labels, y as data values
   - Histogram: use x as labels, y as frequencies
   - Scatter: use x/y as point coordinates
4. DATA TABLE: show the sample rows provided above

CHART STYLING:
- Dark background on all charts
- Colors cycle: #00e5ff, #9d4edd, #00ff87, #ff6b35, #ffd60a
- Rounded bars (borderRadius: 6)
- Subtle gridlines: rgba(255,255,255,0.05)
- Smooth animations

MANDATORY RULES:
- Output ONLY raw HTML. Zero markdown. Zero backticks.
- Start exactly with: <!DOCTYPE html>
- End exactly with: </html>
- All JS in <script> tags at bottom of <body>
- 100% self-contained — no external data fetching
- Use ONLY the data values provided — do not invent numbers
- Render ALL {len(charts_for_prompt)} charts — do not skip any
- Canvas IDs MUST be exactly: chart_1, chart_2, ... chart_{len(charts_for_prompt)}"""


# ── NIM API Call ──────────────────────────────────────────────────────────────

async def _call_nvidia_nim(prompt: str) -> str:
    api_key = os.getenv("NVIDIA_NIM_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="NVIDIA_NIM_API_KEY is not configured in .env")

    models_to_try = [
        "minimaxai/minimax-m2.7",
        "meta/llama-4-maverick-17b-128e-instruct",
        "meta/llama-4-scout-17b-16e-instruct",
        "mistralai/mistral-small-3.1-24b-instruct",
    ]

    last_error = ""

    for model in models_to_try:
        try:
            print(f"=== Trying model: {model} ===")
            # MiniMax M2.7 has specific recommended parameters
            if "minimax" in model:
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an expert BI dashboard developer who writes flawless single-file HTML dashboards. "
                                "You ONLY output raw HTML starting with <!DOCTYPE html> and ending with </html>. "
                                "No markdown, no code fences, no commentary — only the HTML file itself."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 8000,
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "top_k": 40,
                }
            else:
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an expert BI dashboard developer who writes flawless single-file HTML dashboards. "
                                "You ONLY output raw HTML starting with <!DOCTYPE html> and ending with </html>. "
                                "No markdown, no code fences, no commentary — only the HTML file itself."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 8000,
                    "temperature": 0.25,
                }

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            print(f"=== NIM STATUS for {model}: {response.status_code} ===")

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:])
                    if content.endswith("```"):
                        content = content[:-3].strip()
                print(f"=== SUCCESS with model: {model} ===")
                return content
            else:
                last_error = f"{model}: {response.status_code} {response.text[:200]}"
                print(f"=== FAILED {model}: {response.status_code} ===")
                continue

        except httpx.ReadTimeout:
            last_error = f"{model}: ReadTimeout"
            print(f"=== TIMEOUT on model: {model}, trying next ===")
            continue
        except Exception as e:
            last_error = f"{model}: {str(e)}"
            print(f"=== ERROR on model: {model}: {e} ===")
            continue

    raise HTTPException(
        status_code=502,
        detail=f"All NIM models failed. Last error: {last_error}"
    )


async def _call_nim_focused(
    user_prompt: str,
    system_prompt: str,
    max_tokens: int = 3000,
) -> str:
    """
    Focused NIM call with custom system prompt.
    Uses same model fallback chain as _call_nvidia_nim.
    """
    api_key = os.getenv("NVIDIA_NIM_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="NVIDIA_NIM_API_KEY not configured"
        )

    models_to_try = [
        "moonshotai/kimi-k2.6",
        "z-ai/glm-5.1",
        "z-ai/glm-4.7",
        "meta/llama-4-maverick-17b-128e-instruct",
    ]

    last_error = ""
    for model in models_to_try:
        try:
            payload = {
                "model":       model,
                "messages":    [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                "max_tokens":  max_tokens,
            }

            if "kimi" in model or "minimax" in model:
                payload["temperature"] = 1.0
                payload["top_p"]       = 1.0
            elif "glm" in model:
                payload["temperature"]            = 0.2
                payload["chat_template_kwargs"]   = {"thinking": False}
            else:
                payload["temperature"] = 0.2

            if "kimi" in model or "minimax" in model:
                timeout = 90.0
            elif "glm" in model:
                timeout = 120.0
            else:
                timeout = 300.0
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type":  "application/json",
                    },
                    json=payload,
                )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:])
                    if content.endswith("```"):
                        content = content[:-3].strip()
                return content

            last_error = f"{model}: {response.status_code}"
            continue

        except httpx.ReadTimeout:
            last_error = f"{model}: timeout"
            print(f"=== TIMEOUT {model} ===")
            continue
        except Exception as e:
            last_error = f"{model}: {str(e)}"
            continue

    raise HTTPException(
        status_code=502,
        detail=f"All NIM models failed: {last_error}"
    )


def _generate_table_html(
    sample: list,
    max_cols: int = 10,
) -> str:
    """
    Generate a styled HTML data table from sample rows.
    Pure Python — no LLM needed. Always accurate.
    """
    if not sample:
        return ""

    all_cols = list(sample[0].keys())
    cols     = all_cols[:max_cols]
    truncated = len(all_cols) > max_cols

    header_cells = "".join(
        f'<th style="padding:10px 14px;text-align:left;'
        f'font-size:11px;font-weight:600;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:#5c6490;'
        f'border-bottom:1px solid #1e2540;'
        f'white-space:nowrap;">{col}</th>'
        for col in cols
    )

    row_htmls = []
    for i, row in enumerate(sample):
        bg = "#0e1220" if i % 2 == 0 else "#0a0e1a"
        cells = "".join(
            f'<td style="padding:9px 14px;font-size:12px;'
            f'color:#e8eaf6;border-bottom:1px solid #1e2540;'
            f'white-space:nowrap;max-width:180px;'
            f'overflow:hidden;text-overflow:ellipsis;">'
            f'{str(row.get(col, ""))[:50]}</td>'
            for col in cols
        )
        row_htmls.append(
            f'<tr style="background:{bg};">{cells}</tr>'
        )

    rows_html = "\n".join(row_htmls)

    truncation_note = (
        f'<p style="font-size:11px;color:#5c6490;'
        f'margin-top:8px;text-align:right;">'
        f'Showing {len(cols)} of {len(all_cols)} columns</p>'
        if truncated else ""
    )

    return f"""
<section style="margin-top:32px;">
  <div style="display:flex;align-items:center;
              gap:8px;margin-bottom:12px;">
    <div style="width:3px;height:18px;border-radius:2px;
                background:#00e5ff;"></div>
    <span style="font-size:11px;font-weight:600;
                 letter-spacing:0.1em;text-transform:uppercase;
                 color:#00e5ff;">Data Preview</span>
  </div>
  <div style="overflow-x:auto;border-radius:12px;
              border:1px solid #1e2540;">
    <table style="width:100%;border-collapse:collapse;
                  background:#0e1220;">
      <thead>
        <tr style="background:#080b14;">
          {header_cells}
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>
  {truncation_note}
</section>"""


async def _generate_dashboard_multi_call(
    plan: dict,
    filename: str,
) -> str:
    """
    Generates dashboard HTML using 3 focused LLM calls.

    Call 1: Enhance the plan (chart titles, insight labels)
    Call 2: HTML structure + CSS + KPI cards
    Call 3: Chart.js JavaScript code
    Python: Final assembly
    """
    import json

    domain    = plan.get("domain", "general")
    kpis      = plan.get("kpis", [])[:4]
    charts    = plan.get("charts", [])[:6]
    questions = plan.get("business_questions", [])
    summary   = plan.get("executive_summary", "")

    chart_ids = [f"chart_{i+1}" for i in range(len(charts))]
    for i, c in enumerate(charts):
        c["id"] = chart_ids[i]

    # ── Call 1: Plan Enhancement ──────────────────────────────
    print("=== Multi-call: Step 1 — Plan enhancement ===")

    plan_for_enhancement = {
        "domain":   domain,
        "kpis":     [{"label": k["label"],
                      "value": k["formatted_value"]} for k in kpis],
        "charts":   [{"id": c["id"], "type": c["chart_type"],
                      "title": c["title"],
                      "question": c["business_question"]}
                     for c in charts],
    }

    enhancement_prompt = f"""Here is a BI dashboard plan for a {domain} dataset.
Improve ONLY the chart titles and add a one-sentence
insight label for each chart. Keep all IDs unchanged.
Return ONLY valid JSON, nothing else:

{{
  "enhanced_charts": [
    {{
      "id": "chart_1",
      "title": "improved title",
      "insight_label": "one sentence key finding"
    }}
  ],
  "dashboard_subtitle": "one line describing what this dashboard shows"
}}

Plan to enhance:
{json.dumps(plan_for_enhancement, indent=2)}"""

    try:
        enhancement_raw = await _call_nim_focused(
            user_prompt=enhancement_prompt,
            system_prompt="You are a BI analyst. Return only valid JSON.",
            max_tokens=800,
        )
        start = enhancement_raw.find("{")
        end   = enhancement_raw.rfind("}") + 1
        if start >= 0 and end > start:
            enhancement = json.loads(enhancement_raw[start:end])
            enhanced_map = {
                e["id"]: e
                for e in enhancement.get("enhanced_charts", [])
            }
            for c in charts:
                if c["id"] in enhanced_map:
                    c["title"] = enhanced_map[c["id"]].get(
                        "title", c["title"]
                    )
                    c["insight_label"] = enhanced_map[c["id"]].get(
                        "insight_label", ""
                    )
            subtitle = enhancement.get(
                "dashboard_subtitle",
                f"{domain.title()} Analytics Dashboard"
            )
        else:
            subtitle = f"{domain.title()} Analytics Dashboard"
    except Exception as e:
        print(f"=== Enhancement failed, using original plan: {e} ===")
        subtitle = f"{domain.title()} Analytics Dashboard"

    # ── Call 2: HTML Structure + CSS + KPI Cards ──────────────
    print("=== Multi-call: Step 2 — HTML structure + KPIs ===")

    kpis_html_data = json.dumps(
        [{"label": k["label"], "value": k["formatted_value"]}
         for k in kpis],
        indent=2
    )
    canvas_ids = json.dumps(chart_ids)
    chart_titles = json.dumps(
        [{"id": c["id"], "title": c["title"],
          "insight": c.get("insight_label","")}
         for c in charts],
        indent=2
    )

    structure_prompt = f"""Write ONLY the HTML skeleton, CSS styles,
header section, and KPI cards for a BI dashboard.
Do NOT write any Chart.js code or canvas initialization.
Include a comment exactly like this where charts go:
<!-- CHARTS_PLACEHOLDER -->

REQUIREMENTS:
- File: {filename} | Domain: {domain}
- Subtitle: {subtitle}
- Summary: {summary[:200] if summary else ""}

CSS variables to define in :root:
  --bg-primary:#080b14; --bg-card:#0e1220;
  --bg-card-hover:#141828; --border:#1e2540;
  --accent-cyan:#00e5ff; --accent-purple:#9d4edd;
  --accent-green:#00ff87; --accent-orange:#ff6b35;
  --text-primary:#e8eaf6; --text-muted:#5c6490;

Fonts (include CDN):
https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600&display=swap
Tailwind: https://cdn.tailwindcss.com

KPI CARDS (render exactly these {len(kpis)} cards):
{kpis_html_data}

CHART PANELS (create canvas elements with EXACTLY these IDs):
{canvas_ids}
Chart titles and insight labels:
{chart_titles}

Include exactly this comment where the data table goes:
<!-- TABLE_PLACEHOLDER -->
Do NOT generate any table HTML yourself.

Output must:
- Start with <!DOCTYPE html>
- Include Chart.js CDN: https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
- Have <!-- CHARTS_PLACEHOLDER --> exactly once
- End with </body></html> but leave <script> for next step
- Be valid HTML with all sections complete EXCEPT charts JS"""

    structure_html = await _call_nim_focused(
        user_prompt=structure_prompt,
        system_prompt=(
            "You write clean HTML/CSS. Output only raw HTML. "
            "No markdown, no backticks, no explanation."
        ),
        max_tokens=3500,
    )

    print(f"=== Structure HTML: {len(structure_html)} chars ===")

    # ── Call 3: Chart.js JavaScript ───────────────────────────
    print("=== Multi-call: Step 3 — Chart.js code ===")

    charts_data_for_js = []
    for c in charts:
        charts_data_for_js.append({
            "id":      c["id"],
            "type":    c["chart_type"],
            "title":   c["title"],
            "x_label": c.get("x_col", ""),
            "y_label": c.get("y_col", ""),
            "data":    c.get("data", [])[:20],
        })

    js_prompt = f"""Write ONLY the JavaScript code to initialize
{len(charts)} Chart.js charts.

RULES:
- Output ONLY JavaScript — no HTML, no CSS, no <script> tags
- Canvas IDs are EXACTLY: {canvas_ids}
- Use Chart.js 4.4.0 API
- Wrap all code in: document.addEventListener('DOMContentLoaded', function() {{ ... }})
- Dark theme for all charts
- Colors to use: ['#00e5ff','#9d4edd','#00ff87','#ff6b35','#ffd60a']
- Subtle gridlines: rgba(255,255,255,0.05)
- Rounded bars: borderRadius 6
- For each chart: check if canvas exists before initializing

CHARTS TO BUILD:
{json.dumps(charts_data_for_js, indent=2)}

DATA FORMAT:
- bar/line: labels = array of x values, data = array of y values
- donut/pie: labels = array of x values, data = array of y values
- scatter: data = array of {{x, y}} objects
- histogram: labels = bin edges, data = frequencies"""

    charts_js = await _call_nim_focused(
        user_prompt=js_prompt,
        system_prompt=(
            "You write Chart.js 4.4.0 JavaScript. "
            "Output only raw JavaScript code. "
            "No HTML tags, no markdown, no explanation."
        ),
        max_tokens=3000,
    )

    print(f"=== Charts JS: {len(charts_js)} chars ===")

    # ── Python Assembly ───────────────────────────────────────
    print("=== Multi-call: Step 4 — Assembly ===")

    script_block = f"\n<script>\n{charts_js}\n</script>\n"

    if "<!-- CHARTS_PLACEHOLDER -->" in structure_html:
        final_html = structure_html.replace(
            "<!-- CHARTS_PLACEHOLDER -->",
            script_block,
        )
    elif "</body>" in structure_html:
        final_html = structure_html.replace(
            "</body>",
            f"{script_block}</body>",
        )
    else:
        final_html = structure_html + script_block

    # Generate and inject Python data table
    table_html = _generate_table_html(
        plan.get("sample", []),
        max_cols=10,
    )
    if "<!-- TABLE_PLACEHOLDER -->" in final_html:
        final_html = final_html.replace(
            "<!-- TABLE_PLACEHOLDER -->",
            table_html,
        )
    elif table_html:
        final_html = final_html.replace(
            "</body>",
            f'<div style="padding:0 24px 32px;">'
            f'{table_html}</div></body>',
        )

    print(f"=== Final HTML: {len(final_html)} chars ===")
    return final_html


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/bi/generate")
async def generate_bi_dashboard(req: BIDashboardRequest):
    """
    Generate a fully custom HTML BI dashboard for the uploaded dataset
    using NVIDIA NIM (DeepSeek V4 Flash). Returns raw HTML to render in frontend.
    """
    session = get_session(req.session_id)
    if not session or "df" not in session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please upload a dataset first."
        )

    df: pd.DataFrame = session["df"]
    if isinstance(df, list):
        df = pd.DataFrame(df)
    elif isinstance(df, dict):
        df = pd.DataFrame.from_dict(df)

    filename: str = session.get("filename", "dataset.csv")

    plan   = _prepare_plan(df, session)

    print(f"=== BI Dashboard: domain={plan['domain']}, "
          f"source={plan['source']}, "
          f"charts={len(plan['charts'])}, "
          f"kpis={len(plan['kpis'])} ===")

    html_content = await _generate_dashboard_multi_call(plan, filename)

    print(f"=== HTML generated: {len(html_content)} chars ===")

    update_session(req.session_id, "bi_html",   html_content)
    update_session(req.session_id, "bi_domain", plan["domain"])
    update_session(req.session_id, "bi_source", plan["source"])

    return {
        "html_content":     html_content,
        "domain":           plan["domain"],
        "source":           plan["source"],
        "row_count":        plan["row_count"],
        "columns_analyzed": plan["col_count"],
        "charts_count":     len(plan["charts"]),
        "kpis_count":       len(plan["kpis"]),
    }


@router.get("/bi/cached/{session_id}")
def get_cached_bi_dashboard(session_id: str):
    """Return a previously generated dashboard from session cache."""
    session = get_session(session_id)
    if not session or "bi_html" not in session:
        raise HTTPException(status_code=404, detail="No cached BI dashboard found for this session.")
    return {
        "html_content": session["bi_html"],
        "domain":       session.get("bi_domain", "general"),
        "source":       session.get("bi_source", "unknown"),
    }



