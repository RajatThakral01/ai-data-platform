# What Needs to Be Done Next — Detailed Instructions

## Current Status Summary
Everything is working locally with Docker. GitHub is up to date.
The next 4 tasks before this project is production-ready:

```
Task 1: Auto-Dashboard Generator (Metabase API integration)  ← MOST IMPORTANT
Task 2: ECharts (replace Recharts in Data Insights page)
Task 3: Railway deployment (backend)
Task 4: Vercel deployment (frontend)
```

---

# TASK 1 — Auto-Dashboard Generator (Metabase API)

## What It Does
When a user uploads a CSV, your AI already:
- Detects the business domain (telecom, retail, ecommerce)
- Identifies key columns and KPIs
- Generates business questions

**New behavior:** After AI analysis, automatically create a professional Metabase dashboard with the right charts, labeled correctly, organized by business priority. User never has to touch Metabase manually.

## Architecture

```
User uploads CSV
    ↓
Step 1: Save CSV rows to Supabase table (data_{session_id})
Step 2: AI runs insights (already working)
Step 3: Auto-dashboard generator reads AI insights
Step 4: Creates Metabase questions via Metabase REST API
Step 5: Creates Metabase dashboard and adds charts
Step 6: Returns dashboard URL to frontend
Step 7: Frontend shows "View Dashboard" button
```

## Step 1 — Save CSV to Supabase on Upload

### Before writing any code, find the Metabase database ID:
Go to `localhost:3001` → Admin settings → Databases → click "AI Data Platform" → look at URL: `/admin/databases/2` → ID is 2 (or whatever number you see)

### New Supabase table needed (run in Supabase SQL Editor):
```sql
-- This stores uploaded data so Metabase can visualize it
-- We create one view per session, not one table per session
-- (creating tables dynamically requires superuser permissions)
-- Instead, store all data in one table with session_id column

create table uploaded_data (
  id bigserial primary key,
  session_id uuid not null,
  filename text,
  row_index int,
  data jsonb,  -- each row stored as JSON
  created_at timestamptz default now()
);

create index on uploaded_data(session_id);
```

### Copilot Prompt for Step 1:

**TASK:** Save CSV data to Supabase on upload
**MODEL:** Claude Haiku 4.5
**MODE:** Agent

```
In backend/routers/upload.py, after the line:
    update_session(session_id, "filename", file.filename)

Add this code to save data to Supabase:

    # Save to Supabase for Metabase visualization
    try:
        from db.supabase_client import get_supabase
        supabase = get_supabase()
        if supabase:
            rows = []
            df_for_upload = df.where(pd.notnull(df), None)
            for idx, row in df_for_upload.head(1000).iterrows():
                rows.append({
                    "session_id": session_id,
                    "filename": file.filename,
                    "row_index": int(idx),
                    "data": row.to_dict()
                })
            # Insert in batches of 100
            for i in range(0, len(rows), 100):
                batch = rows[i:i+100]
                supabase.table("uploaded_data").insert(batch).execute()
    except Exception as e:
        print(f"Supabase data upload failed (non-critical): {e}")

Show me the updated upload section.
```

## Step 2 — Metabase API Client

### Copilot Prompt for Step 2:

**TASK:** Create Metabase API client
**MODEL:** GPT-5.2-Codex
**MODE:** Agent

```
Create a new file backend/metabase/client.py with this content:

import os
import requests
import logging

logger = logging.getLogger(__name__)

METABASE_URL = os.getenv("METABASE_SITE_URL", "http://localhost:3001")
METABASE_EMAIL = os.getenv("METABASE_EMAIL", "")
METABASE_PASSWORD = os.getenv("METABASE_PASSWORD", "")

_token = None

def get_token() -> str | None:
    global _token
    if _token:
        return _token
    try:
        resp = requests.post(
            f"{METABASE_URL}/api/session",
            json={"username": METABASE_EMAIL, "password": METABASE_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            _token = resp.json()["id"]
            return _token
    except Exception as e:
        logger.error(f"Metabase auth failed: {e}")
    return None

def metabase_get(path: str) -> dict | None:
    token = get_token()
    if not token:
        return None
    try:
        resp = requests.get(
            f"{METABASE_URL}{path}",
            headers={"X-Metabase-Session": token},
            timeout=10
        )
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        logger.error(f"Metabase GET {path} failed: {e}")
        return None

def metabase_post(path: str, data: dict) -> dict | None:
    token = get_token()
    if not token:
        return None
    try:
        resp = requests.post(
            f"{METABASE_URL}{path}",
            headers={"X-Metabase-Session": token},
            json=data,
            timeout=15
        )
        return resp.json() if resp.status_code in [200, 202] else None
    except Exception as e:
        logger.error(f"Metabase POST {path} failed: {e}")
        return None

def get_database_id() -> int | None:
    """Find the AI Data Platform database ID in Metabase."""
    dbs = metabase_get("/api/database")
    if not dbs:
        return None
    for db in dbs.get("data", []):
        if "AI Data Platform" in db.get("name", "") or "supabase" in db.get("details", {}).get("host", "").lower():
            return db["id"]
    return None

def get_table_id(database_id: int, table_name: str) -> int | None:
    """Find a table ID by name in Metabase."""
    tables = metabase_get(f"/api/database/{database_id}/metadata")
    if not tables:
        return None
    for table in tables.get("tables", []):
        if table.get("name", "").lower() == table_name.lower():
            return table["id"]
    return None

Also create backend/metabase/__init__.py (empty file).

Show me both files.
```

## Step 3 — Auto Dashboard Generator

### Copilot Prompt for Step 3:

**TASK:** Create auto-dashboard generator
**MODEL:** GPT-5.2-Codex
**MODE:** Agent

```
Create backend/metabase/auto_dashboard.py with this content:

import logging
from .client import metabase_post, metabase_get, get_database_id, get_table_id

logger = logging.getLogger(__name__)

CHART_COLORS = ["#00d4ff", "#7b2fff", "#ff6b35", "#00ff88", "#d4b100"]

def create_dashboard(session_id: str, filename: str, domain: str, 
                     insights: dict) -> str | None:
    """
    Auto-create a Metabase dashboard based on AI insights.
    Returns the dashboard URL or None if failed.
    """
    try:
        db_id = get_database_id()
        if not db_id:
            logger.error("Could not find Metabase database ID")
            return None

        table_id = get_table_id(db_id, "uploaded_data")
        if not table_id:
            logger.error("Could not find uploaded_data table in Metabase")
            return None

        # Get field IDs from the table
        table_meta = metabase_get(f"/api/table/{table_id}/query_metadata")
        fields = {}
        if table_meta:
            for field in table_meta.get("fields", []):
                fields[field["name"]] = field["id"]

        # Create dashboard
        dashboard = metabase_post("/api/dashboard", {
            "name": f"AI Analysis: {filename}",
            "description": f"Auto-generated dashboard for {filename} | Domain: {domain}",
            "parameters": []
        })
        
        if not dashboard:
            logger.error("Failed to create Metabase dashboard")
            return None
        
        dashboard_id = dashboard["id"]

        # Create cards based on domain and insights
        charts = _get_charts_for_domain(domain, insights, fields, table_id, db_id, session_id)
        
        # Add cards to dashboard
        for i, chart_def in enumerate(charts[:5]):  # max 5 charts
            card = metabase_post("/api/card", chart_def)
            if card:
                metabase_post(f"/api/dashboard/{dashboard_id}/cards", {
                    "cardId": card["id"],
                    "col": (i % 2) * 12,
                    "row": (i // 2) * 8,
                    "size_x": 12,
                    "size_y": 8
                })

        from .client import METABASE_URL
        return f"{METABASE_URL}/dashboard/{dashboard_id}"

    except Exception as e:
        logger.error(f"Auto-dashboard creation failed: {e}")
        return None


def _get_charts_for_domain(domain, insights, fields, table_id, db_id, session_id):
    """Generate chart definitions based on detected domain."""
    charts = []
    
    # Always add a data overview chart
    charts.append(_make_row_count_card(table_id, db_id, session_id))
    
    # Domain-specific charts
    domain_charts = {
        "telecom": _telecom_charts,
        "retail": _retail_charts,
        "ecommerce": _retail_charts,
        "finance": _finance_charts,
    }
    
    chart_fn = domain_charts.get(domain.lower(), _generic_charts)
    charts.extend(chart_fn(fields, table_id, db_id, session_id, insights))
    
    return [c for c in charts if c is not None]


def _make_row_count_card(table_id, db_id, session_id):
    return {
        "name": "Total Records",
        "display": "scalar",
        "dataset_query": {
            "database": db_id,
            "type": "query",
            "query": {
                "source-table": table_id,
                "filter": ["=", ["field", "session_id", {"base-type": "type/Text"}], session_id],
                "aggregation": [["count"]]
            }
        },
        "visualization_settings": {}
    }


def _telecom_charts(fields, table_id, db_id, session_id, insights):
    return [
        {
            "name": "Churn Distribution",
            "display": "pie",
            "dataset_query": {
                "database": db_id,
                "type": "native",
                "native": {
                    "query": f"""
                    SELECT (data->>'churn_flag')::text as churn_status, COUNT(*) as count
                    FROM uploaded_data 
                    WHERE session_id = '{session_id}'
                    GROUP BY churn_status
                    """
                }
            },
            "visualization_settings": {"pie.colors": {"true": "#ff6b35", "false": "#00ff88"}}
        },
        {
            "name": "Contract Type vs Churn",
            "display": "bar",
            "dataset_query": {
                "database": db_id,
                "type": "native",
                "native": {
                    "query": f"""
                    SELECT (data->>'contract_type')::text as contract_type, COUNT(*) as count
                    FROM uploaded_data 
                    WHERE session_id = '{session_id}'
                    GROUP BY contract_type
                    ORDER BY count DESC
                    """
                }
            },
            "visualization_settings": {}
        }
    ]


def _retail_charts(fields, table_id, db_id, session_id, insights):
    return [
        {
            "name": "Revenue Distribution",
            "display": "bar",
            "dataset_query": {
                "database": db_id,
                "type": "native",
                "native": {
                    "query": f"""
                    SELECT (data->>'category')::text as category, 
                           SUM((data->>'sales')::float) as total_sales
                    FROM uploaded_data 
                    WHERE session_id = '{session_id}'
                    GROUP BY category
                    ORDER BY total_sales DESC
                    LIMIT 10
                    """
                }
            },
            "visualization_settings": {}
        }
    ]


def _finance_charts(fields, table_id, db_id, session_id, insights):
    return _generic_charts(fields, table_id, db_id, session_id, insights)


def _generic_charts(fields, table_id, db_id, session_id, insights):
    return [
        {
            "name": "Data Overview",
            "display": "table",
            "dataset_query": {
                "database": db_id,
                "type": "native",
                "native": {
                    "query": f"""
                    SELECT data FROM uploaded_data 
                    WHERE session_id = '{session_id}'
                    LIMIT 100
                    """
                }
            },
            "visualization_settings": {}
        }
    ]

Show me the complete file.
```

## Step 4 — Wire Auto-Dashboard into Insights Endpoint

### Copilot Prompt for Step 4:

**TASK:** Trigger auto-dashboard after insights run
**MODEL:** Claude Haiku 4.5
**MODE:** Agent

```
In backend/routers/insights.py, find the return statement 
at the end of the POST /api/insights endpoint.

Before the return statement, add this code:

    # Auto-generate Metabase dashboard in background
    try:
        import threading
        from metabase.auto_dashboard import create_dashboard
        domain = result.get("domain", "general")
        def _create_dashboard():
            url = create_dashboard(
                session_id=body.get("session_id"),
                filename=session.get("filename", "dataset"),
                domain=domain,
                insights=result
            )
            if url:
                print(f"Metabase dashboard created: {url}")
        threading.Thread(target=_create_dashboard, daemon=True).start()
    except Exception as e:
        print(f"Auto-dashboard trigger failed (non-critical): {e}")

Also add "dashboard_url": None to the return dict 
(we'll populate it later via polling).

Show me the updated return section.
```

---

# TASK 2 — ECharts Integration

## What It Does
Replace Recharts (4-5 basic chart types) with Apache ECharts (30+ types, interactive, zoomable).

## Installation

**Copilot Prompt:**

**TASK:** Install ECharts
**MODEL:** Grok Code Fast 1
**MODE:** Agent

```
Run in terminal from /Users/rajatthakral/ai-data-platform/frontend:
npm install echarts echarts-for-react

Show me the output.
```

## Replace Data Insights Charts

**TASK:** Replace Recharts with ECharts in insights page
**MODEL:** GPT-5.2-Codex
**MODE:** Agent

```
Read frontend/app/dashboard/insights/page.tsx completely.

Find all Recharts imports and components:
- BarChart, LineChart, ScatterChart, PieChart
- XAxis, YAxis, CartesianGrid, Tooltip, Legend
- Bar, Line, Scatter, Pie, Cell, ResponsiveContainer

Replace them with ECharts using echarts-for-react.

For each chart in the page, convert to ECharts option format:

BAR CHART example:
import ReactECharts from 'echarts-for-react';
const option = {
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: labels, axisLabel: { color: '#64748b' } },
  yAxis: { type: 'value', axisLabel: { color: '#64748b' } },
  series: [{ data: values, type: 'bar', itemStyle: { color: '#00d4ff' } }],
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true }
};
<ReactECharts option={option} style={{height: '300px'}} theme="dark" />

LINE CHART example:
const option = {
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: labels, axisLabel: { color: '#64748b' } },
  yAxis: { type: 'value', axisLabel: { color: '#64748b' } },
  series: [{ data: values, type: 'line', smooth: true, 
             lineStyle: { color: '#7b2fff' }, 
             areaStyle: { color: 'rgba(123, 47, 255, 0.1)' } }]
};

PIE CHART example:
const option = {
  backgroundColor: 'transparent',
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie', radius: '60%',
    data: data.map((v, i) => ({ 
      value: v, name: labels[i],
      itemStyle: { color: ['#00d4ff','#7b2fff','#ff6b35','#00ff88','#d4b100'][i % 5] }
    }))
  }]
};

Convert ALL charts in the file to ECharts format.
Keep all existing data fetching and state management unchanged.
Only change the chart rendering components.

Show me the complete updated file.
```

---

# TASK 3 — Railway Deployment (Backend)

## Pre-deployment Checklist
Before deploying, run this locally:
```bash
curl http://localhost:8000/health
# Should return: {"status": "ok"}
```

## Steps (do in browser at railway.app)

1. Go to **railway.app** → Sign in with GitHub
2. **New Project → Deploy from GitHub**
3. Select `RajatThakral01/ai-data-platform`
4. **Root Directory:** `backend`
5. **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. **Add environment variables** (copy from your .env):
   ```
   GROQ_API_KEY=...
   GEMINI_API_KEY=...
   SUPABASE_URL=...
   SUPABASE_KEY=...
   FRONTEND_URL=https://your-app.vercel.app  (update after Vercel deploy)
   ```
7. **Add Redis:** New → Database → Redis → copy REDIS_URL → add as env var
8. Test: `curl https://your-railway-url.railway.app/health`

## Add Dockerfile for Railway (more reliable than auto-detect)

**TASK:** Create Railway-specific config
**MODEL:** Grok Code Fast 1
**MODE:** Agent

```
Create a file backend/railway.toml with this content:

[build]
builder = "DOCKERFILE"
dockerfilePath = "backend/Dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

Show me the file.
```

---

# TASK 4 — Vercel Deployment (Frontend)

## Steps (do in browser at vercel.com)

1. Go to **vercel.com** → Sign in with GitHub
2. **New Project → Import** `RajatThakral01/ai-data-platform`
3. **Root Directory:** `frontend`
4. **Framework:** Next.js (auto-detected)
5. **Add environment variables:**
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
   ```
6. Deploy
7. Copy Vercel URL → go back to Railway → update `FRONTEND_URL` env var

## Update CORS after deployment

**TASK:** Update CORS for production
**MODEL:** Grok Code Fast 1
**MODE:** Agent

```
In backend/main.py, find the allow_origins list and update it to:
    allow_origins=[
        "http://localhost:3000",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "https://*.vercel.app",
    ],

Show me the updated CORS section.
```

---

# Order of Execution

```
1. Run SQL for uploaded_data table in Supabase dashboard
2. Task 1 Step 1 — Save CSV to Supabase on upload
3. Task 1 Step 2 — Metabase API client
4. Task 1 Step 3 — Auto-dashboard generator
5. Task 1 Step 4 — Wire into insights endpoint
6. Test auto-dashboard locally
7. Task 2 — ECharts (install + replace charts)
8. Commit everything: git add -A && git commit -m "feat: auto-dashboard + ECharts" && git push
9. Task 3 — Railway deployment
10. Task 4 — Vercel deployment
11. Update FRONTEND_URL in Railway with Vercel URL
12. End-to-end test on live URLs
```

---

*Last updated: March 19, 2026*
