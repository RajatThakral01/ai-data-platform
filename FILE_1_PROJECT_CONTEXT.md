# AI Data Analysis Platform — Complete Project Context (March 19, 2026)

## Student Info
- **Name:** Rajat Thakral
- **Roll No:** 2022BTECH080
- **Institution:** JKLU
- **Project:** BTech PS-II — AI-Powered Data Analysis Platform
- **GitHub:** github.com/RajatThakral01/ai-data-platform

---

## What This Project Is

A full-stack, AI-powered, no-code data analysis platform. A user uploads any CSV or Excel file and gets:
- Automated EDA (exploratory data analysis)
- Smart data cleaning with recommendations
- ML model training and evaluation
- AI-generated business insights with charts
- Natural language querying ("what is the average churn rate?")
- PDF report generation
- LLM observability dashboard
- Metabase BI dashboard integration

**The core pitch:** "Upload any CSV. Get a data analyst's full report in 60 seconds. No expertise needed."

---

## Architecture — 5 Layers

```
Browser (port 3000)
    ↓
Next.js 14 Frontend (cyberpunk dark theme)
    ↓ axios REST calls
FastAPI Backend (port 8000)
    ↓ sys.path imports
Streamlit Python Modules (analysis engine)
    ↓
Groq API → Gemini API → Ollama (LLM fallback chain)
    ↓
Supabase (PostgreSQL + pgvector) + Redis (sessions)
```

**Plus:** Metabase (port 3001) — connected to Supabase for BI dashboards

---

## Current File Structure (Updated March 2026)

```
/Users/rajatthakral/ai-data-platform/
├── .env                           ← ALL secrets (DO NOT TOUCH, DO NOT COMMIT)
├── .gitignore                     ← includes venv/, .env, node_modules/
├── .dockerignore
├── docker-compose.yml             ← runs all 5 services
├── start.sh
├── README.md
│
├── streamlit/                     ← ORIGINAL APP (DO NOT MODIFY)
│   ├── app.py
│   ├── modules/
│   │   ├── eda.py
│   │   ├── data_cleaner.py
│   │   ├── ml_engine.py
│   │   ├── data_insights.py
│   │   ├── nl_query.py
│   │   └── report_gen.py
│   ├── llm/
│   │   ├── client_factory.py      ← Groq → Gemini → Ollama routing
│   │   ├── groq_client.py
│   │   ├── gemini_client.py
│   │   └── ollama_client.py
│   ├── rag/
│   │   ├── embedder.py            ← PageIndex chunking (UPGRADED)
│   │   ├── vector_store.py        ← pgvector + ChromaDB fallback (UPGRADED)
│   │   ├── rag_query.py           ← hybrid search (UPGRADED)
│   │   └── document_processor.py ← background indexing on upload
│   ├── utils/
│   │   └── llm_logger.py          ← logs to Supabase + SQLite fallback
│   └── requirements.txt
│
├── backend/
│   ├── main.py                    ← FastAPI app, CORS, router registration
│   ├── session_store.py           ← Supabase + Redis + memory fallback
│   ├── db/
│   │   ├── __init__.py
│   │   └── supabase_client.py     ← singleton Supabase client
│   └── routers/
│       ├── upload.py              ← POST /api/upload
│       ├── eda.py                 ← POST /api/eda
│       ├── cleaning.py            ← POST /api/clean
│       ├── ml.py                  ← POST /api/ml
│       ├── insights.py            ← POST /api/insights
│       ├── nl_query.py            ← POST /api/query (UPGRADED)
│       ├── report.py              ← POST /api/report
│       ├── observatory.py         ← GET /api/observatory/stats|logs
│       ├── query_clusters.py      ← GET /api/query-clusters (NEW)
│       └── export.py              ← GET /api/export/{session_id} (NEW)
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx               ← Landing/upload page
│   │   ├── globals.css            ← Cyberpunk design system
│   │   └── dashboard/
│   │       ├── page.tsx           ← Command Center
│   │       ├── eda/page.tsx
│   │       ├── cleaning/page.tsx
│   │       ├── ml/page.tsx
│   │       ├── insights/page.tsx
│   │       ├── query/page.tsx     ← NL Query (UPGRADED with follow-ups)
│   │       ├── observatory/page.tsx
│   │       ├── report/page.tsx
│   │       └── advanced/page.tsx  ← Metabase BI Dashboard (NEW)
│   ├── components/
│   │   └── Sidebar.tsx            ← includes BI Dashboard nav item
│   └── lib/
│       ├── api.ts
│       ├── store.tsx
│       └── types.ts               ← includes all updated interfaces
│
├── docker-compose.yml             ← 5 services: redis, backend, frontend, streamlit, metabase
└── tests/                         ← 167 unit tests
```

---

## Docker Services (docker-compose.yml)

| Service | Port | What |
|---|---|---|
| `ai_platform_redis` | 6379 | Session cache (Redis 7, maxmemory 256mb) |
| `ai_platform_backend` | 8000 | FastAPI |
| `ai_platform_frontend` | 3000 | Next.js 14 |
| `ai_platform_streamlit` | 8501 | Streamlit legacy |
| `ai_platform_metabase` | 3001 | Metabase BI (H2 db, connected to Supabase) |

**Start everything:**
```bash
cd /Users/rajatthakral/ai-data-platform
docker-compose up
```

**Rebuild a single service:**
```bash
docker-compose build --no-cache backend && docker-compose up
```

---

## Environment Variables (.env file)

```
GROQ_API_KEY=...
GEMINI_API_KEY=...
SUPABASE_URL=https://rhqewolgahcbewrjhzzk.supabase.co
SUPABASE_KEY=...
REDIS_URL=redis://redis:6379  (set automatically in docker-compose)
FRONTEND_URL=http://localhost:3000
METABASE_SITE_URL=http://localhost:3001
METABASE_EMBEDDING_SECRET=...  (rotated, new value in .env)
METABASE_EMAIL=...
METABASE_PASSWORD=...
```

---

## Supabase Schema (all tables created)

```sql
-- Sessions
sessions (id uuid, created_at, expires_at, filename, row_count, metadata jsonb)

-- LLM Logs (replaces SQLite llm_logs.db)
llm_logs (id, session_id, created_at, module_name, model_used, 
          prompt_tokens, completion_tokens, latency_ms, success, 
          fallback_used, cost, error_message)

-- Vector chunks (replaces ChromaDB)
document_chunks (id, session_id, created_at, chunk_text, page_num, 
                 embedding vector(384), metadata jsonb)

-- NL Query History (NEW)
nl_query_history (id, session_id, created_at, question, answer, 
                  query_type, summary, follow_ups jsonb, 
                  execution_time_ms, success, embedding vector(384))
```

**SQL functions:**
```sql
match_chunks(query_embedding, session_id_filter, match_count)  ← vector similarity search
```

---

## All API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/upload | Upload CSV/XLSX, create session, trigger RAG indexing |
| POST | /api/eda | Run EDA |
| POST | /api/clean | Clean data |
| POST | /api/ml | Train ML models |
| POST | /api/insights | AI business insights |
| POST | /api/query | NL query (returns answer + query_type + summary + follow_ups) |
| POST | /api/report | Generate PDF |
| GET | /api/observatory/stats | LLM stats from Supabase |
| GET | /api/observatory/logs | Last 50 LLM logs |
| GET | /api/query-clusters | HDBSCAN query clustering |
| GET | /api/export/{session_id} | Export data as JSON (for Metabase) |
| GET | /api/export/{session_id}/csv | Download as CSV |
| GET | /health | Health check |

---

## What's Working ✅

| Feature | Status |
|---|---|
| File upload (CSV, XLSX, XLS) | ✅ |
| Smart EDA | ✅ |
| Data Cleaning | ✅ |
| ML Recommender | ✅ |
| AI Data Insights | ✅ |
| NL Query with follow-ups + summary | ✅ |
| Query classification (trend/aggregation/filter/description) | ✅ |
| HDBSCAN query clustering | ✅ |
| PDF Report | ✅ |
| LLM Observatory | ✅ |
| PageIndex RAG + pgvector hybrid search | ✅ |
| Supabase sessions + LLM logs | ✅ |
| Redis session cache | ✅ |
| Docker all 5 services | ✅ |
| Metabase connected to Supabase | ✅ |
| Data export endpoints | ✅ |
| GitHub repo up to date | ✅ |

---

## Tech Stack (Updated)

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts, shadcn/ui |
| Backend | FastAPI, Python 3.12, uvicorn |
| AI/LLM | Groq (Llama 3.3 70B) → Gemini 2.0 Flash → Ollama Mistral 7B |
| RAG | Supabase pgvector + sentence-transformers (PageIndex chunking) |
| Vector Search | Hybrid: pgvector similarity + PostgreSQL full-text |
| Query Clustering | HDBSCAN |
| Sessions | Supabase (primary) + Redis (cache) + memory (fallback) |
| LLM Logs | Supabase (primary) + SQLite (fallback) |
| ML | scikit-learn (LogisticRegression, RandomForest, GradientBoosting) |
| PDF Reports | fpdf2 |
| BI Dashboard | Metabase (connected to Supabase) |
| Orchestration | Docker Compose (5 services) |

---

## Critical Rules (Never Break These)

1. **NEVER modify streamlit/ folder** — original working app
2. **NEVER move venv/** — breaks all Python deps
3. **NEVER delete .env** — contains API keys
4. **NEVER push .env to GitHub** — gitignored
5. **Always reconstruct DataFrame** from session: `if isinstance(df, (list, dict)): df = pd.DataFrame(df)`
6. **Always clean NaN** before returning JSON from FastAPI
7. **Always use `os.path.dirname(__file__)`** for paths — no hardcoded /Users/rajatthakral paths
8. **sys.path must use relative paths** in all routers

---

## Frontend Design System

```css
--bg-primary: #0a0a0f
--bg-card: #0f0f1a
--accent-cyan: #00d4ff
--accent-purple: #7b2fff
--accent-orange: #ff6b35
--accent-green: #00ff88
--text-primary: #e2e8f0
--text-muted: #64748b
--border-subtle: rgba(0, 212, 255, 0.15)
```

Chart colors: `["#00d4ff", "#7b2fff", "#ff6b35", "#00ff88", "#d4b100"]`
CSS classes: `.data-card`, `.grid-bg`
Fonts: Inter (UI), JetBrains Mono (numbers/code)

---

*Last updated: March 19, 2026*
