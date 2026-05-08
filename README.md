# 🧠 AI-Powered Analytics Platform

<p align="center">
  <b>From raw data → production-grade BI dashboards, with zero coding required.</b><br/>
  A 7-module agentic analytics platform powered by multi-tier LLM routing, smart chart planning, and AI-generated BI dashboards.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js_14-000000?style=for-the-badge&logo=next.js&logoColor=white" />
  <img src="https://img.shields.io/badge/NVIDIA_NIM-76B900?style=for-the-badge&logo=nvidia&logoColor=white" />
  <img src="https://img.shields.io/badge/Groq-FF6B35?style=for-the-badge" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Tests-167%2F167_Passing-22c55e?style=for-the-badge" />
</p>

---

## 📌 What Is This?

Most data analysis tools require either coding expertise or expensive SaaS subscriptions. This platform eliminates both.

Upload **any tabular dataset** → get automated EDA, AI-generated insights, ML recommendations, natural language querying, and a fully custom **production-grade BI dashboard** — no code, no setup, no expertise required.

Built for data analysts, product managers, and non-technical decision-makers who need fast, reliable answers from their data — and professional dashboards they can share with stakeholders.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 📊 **Smart EDA** | Automated exploratory analysis — distributions, correlations, outliers, column typing |
| 💡 **AI Insights Engine** | Business-context-aware insights with KPIs, charts, and executive summary |
| 🗣️ **NL Query Engine** | Ask questions in plain English — gets converted to pandas and executed |
| 🤖 **ML Recommender** | Suggests optimal ML algorithm based on data shape and target variable |
| 📈 **AI BI Dashboard** | Auto-generated, domain-specific HTML dashboards via NVIDIA NIM multi-call architecture |
| 🔁 **Multi-Tier LLM Routing** | Groq → Gemini → Ollama with automatic failover for core modules |
| 🧠 **Smart Chart Planner** | Domain-aware chart decision engine using business questions library |
| ✅ **167/167 Tests Passing** | Fully tested across all modules |

---

## 🏗️ Architecture

```
  📂 Input Dataset (CSV / Excel)
         │
         ▼
  ┌─────────────────────────────────────────────┐
  │           DATA INGESTION LAYER              │
  │     Validation · Session Store · Profiling  │
  └──────────────────┬──────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌──────────┐  ┌────────────┐  ┌────────────┐
│ Smart    │  │    Data    │  │     ML     │
│   EDA    │  │  Insights  │  │ Recommender│
└──────────┘  └────────────┘  └────────────┘
    │                │
    └────────────────┘
             │ eda_results + insights_results
             │ stored in session
             ▼
  ┌─────────────────────────────────────────────┐
  │         SMART CHART DECISION ENGINE         │
  │  Domain Mapper → Business Questions →       │
  │  Chart Planner → Validated Plan             │
  └──────────────────┬──────────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────────┐
  │        AI BI DASHBOARD GENERATION           │
  │                                             │
  │   NVIDIA NIM Multi-Call Architecture:       │
  │   Call 1: Plan Enhancement   (800 tokens)   │
  │   Call 2: HTML + CSS + KPIs (3500 tokens)   │
  │   Call 3: Chart.js JS       (3000 tokens)   │
  │   Python: Assembly + Table  (no LLM)        │
  │                                             │
  │   Model Chain (fallback):                   │
  │   Kimi K2.6 → GLM-5.1 → GLM-4.7            │
  │   → Llama 4 Maverick                        │
  └──────────────────┬──────────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────────┐
  │               OUTPUT LAYER                  │
  │  BI Dashboard · Reports · NL Answers        │
  │  Downloadable HTML · Data Table             │
  └─────────────────────────────────────────────┘
```

---

## 🧩 Modules Breakdown

### 1. 📊 Smart EDA
Automated exploratory data analysis — detects data types, distributions, missing values, correlations, and outliers without writing a single line of pandas.

**Returns:**
- `stats` — describe() output per numeric column
- `missing` — column-level missing value percentages
- `correlations` — Pearson correlation matrix
- `outliers` — IQR-based outlier counts per column
- `column_types` — numeric / categorical / datetime classification

Results are stored in session and consumed by the Insights and BI Dashboard modules downstream.

---

### 2. 💡 AI Insights Engine
Five-step pipeline that produces business-relevant analysis of your dataset:

**Step 1 — Business Context Detection**
LLM identifies domain (telecom/retail/finance/HR/marketing etc.), target metric, KPI columns, and 5 business questions specific to your data.

**Step 2 — KPI Extraction**
Pure pandas computation of primary KPIs — no LLM needed, always accurate.

**Step 3 — Chart Generation**
LLM proposes 5 analytically relevant chart specs. Each spec is then validated by `_validate_chart_spec()` before execution — checking column existence, numeric type requirements, cardinality limits for pie charts, and aggregation logic.

**Step 4 — Correlation Chart**
Python automatically appends a correlation bar chart showing which features most influence the target metric. Always analytically relevant, zero LLM involvement.

**Step 5 — AI Bullet Insights**
LLM generates 5 CEO-level insights referencing actual computed KPI values, chart findings, top correlations, and outlier counts — not generic advice.

**Also generates:** Executive Summary (2-sentence dataset overview with specific numbers), rendered on the Insights page.

---

### 3. 🗣️ Natural Language Query Engine
Ask your data anything in plain English:
> *"What's the average monthly charges by contract type?"*
> *"Which customers have the highest churn risk?"*

Text → Python (pandas) → executed → result returned as a renderable table.

---

### 4. 🤖 ML Recommender
Analyzes your dataset's shape, target variable type, and class balance — then recommends the optimal ML algorithm and preprocessing steps (one-hot encoding, normalization, handling imbalance).

---

### 5. 📈 AI BI Dashboard *(New)*

The flagship feature — generates a fully custom, professional-grade HTML BI dashboard tailored to your specific dataset and business domain.

#### Smart Chart Decision Engine
Before any LLM call, Python builds a validated dashboard plan:

**Domain Column Mapper** (`utils/domain_mapper.py`)
Fuzzy-matches DataFrame columns to semantic roles across 10 domains:
```
telecom:    churn_col, tenure_col, charges_col, contract_col...
retail:     revenue_col, product_col, date_col, quantity_col...
finance:    amount_col, fraud_col, risk_col, balance_col...
hr:         attrition_col, salary_col, department_col...
marketing:  campaign_col, ctr_col, conversion_col, channel_col...
```

**Business Questions Library** (`utils/business_questions.py`)
Predefined analytically-relevant questions per domain, each mapped to a chart type and column roles:
```python
"telecom": [
  { "question": "What is the overall churn rate?",
    "chart_type": "donut", "x_role": "churn_col", "priority": 1 },
  { "question": "Which contract type has the highest churn?",
    "chart_type": "bar", "x_role": "contract_col", "priority": 1 },
  ...
]
```

**Chart Plan Builder** (`utils/chart_planner.py`)
- **Path 1**: If Data Insights has already run → uses `insights_results` from session directly (domain, KPIs, charts, business questions already computed)
- **Path 2**: Builds from scratch using domain mapper + business questions + pandas computations

Either way, the LLM receives a validated plan with **real data baked in** — not raw stats.

#### Multi-Call HTML Generation
Three focused LLM calls instead of one massive prompt:

```
Call 1 (800 tokens)  → Plan enhancement: better titles, insight labels
Call 2 (3500 tokens) → HTML skeleton + CSS + KPI cards
                       (includes <!-- CHARTS_PLACEHOLDER -->)
Call 3 (3000 tokens) → Chart.js JavaScript only
                       (canvas IDs injected from Call 2)

Python Assembly      → Injects JS into placeholder
                     → Generates data table (pure Python, always accurate)
                     → Returns complete 20-30KB HTML file
```

#### NVIDIA NIM Model Chain
```
Kimi K2.6           (primary — best frontend design, 58.6% SWE-Bench Pro)
    ↓ timeout (90s)
GLM-5.1             (secondary — top coding benchmark, UI-specialized)
    ↓ timeout (120s)
GLM-4.7             (tertiary — agentic coding + UI skills)
    ↓ timeout
Llama 4 Maverick    (reliable fallback — proven working, always fast)
```

#### Dashboard Output
- Dark-themed professional UI (Power BI / Tableau aesthetic)
- KPI cards with real computed values
- 5-6 business-relevant charts (Chart.js — bar, line, donut, scatter, histogram)
- Insight label under each chart explaining the key finding
- Python-generated data preview table
- Fully downloadable as a standalone `.html` file
- Source badge: **✦ From Insights** / **⚡ Auto-planned**

---

### 6. 🔁 LLM Routing

**Core Modules** (EDA narration, NL Query, ML, Insights):
```
Request ──► Groq (primary — fastest, Llama 3.3-70B / 3.1-8B)
              │ (if rate-limited)
              ▼
           Gemini (secondary — gemini-2.0-flash)
              │ (if quota exceeded)
              ▼
           Ollama (local fallback — mistral/llama3)
```

**BI Dashboard** (NVIDIA NIM — separate from core chain):
```
Kimi K2.6 → GLM-5.1 → GLM-4.7 → Llama 4 Maverick
```

---

### 7. 🧪 Test Suite
167 tests across all modules ensuring reliability at every layer:
- `test_data_loader.py` — pandas safety and ingestion
- `test_nl_query.py` — text-to-code parser
- `test_ml.py` — ML recommendation logic
- `test_prompts.py` — prompt template validation
- `test_report_gen.py` — report generation
- `test_ollama_client.py` — LLM client failover

---

## 🚀 Getting Started

### Prerequisites
```bash
Python 3.10+
Node.js 18+
Groq API Key        # https://console.groq.com
Gemini API Key      # https://aistudio.google.com
NVIDIA NIM API Key  # https://build.nvidia.com (free, no credit card)
Ollama (optional)   # https://ollama.ai — for local fallback
```

### Installation

```bash
# Clone the repo
git clone https://github.com/RajatThakral01/ai-data-platform.git
cd ai-data-platform

# Install and run using Docker (Recommended)
docker-compose up --build -d
# Platform available at http://localhost:3000
```

### Configuration

```bash
# Copy the example env file
cp .env.example .env
```

Edit `.env` with your keys:

```env
# Core LLM providers
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here

# NVIDIA NIM — required for AI BI Dashboard
NVIDIA_NIM_API_KEY=nvapi-your_nvidia_nim_key_here

# Optional
REDIS_URL=redis://localhost:6379
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
FRONTEND_URL=http://localhost:3000
```

### Run Locally (Without Docker)

```bash
# Backend
cd backend
pip install -r requirements_backend.txt
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Open http://localhost:3000
```

### Run Tests

```bash
cd backend
pytest tests/ -v
# Expected: 167 passed
```

---

## 📁 Project Structure

```
ai-data-platform/
├── backend/
│   ├── routers/
│   │   ├── upload.py           # CSV/Excel ingestion + session init
│   │   ├── eda.py              # Smart EDA — stats, correlations, outliers
│   │   ├── insights.py         # AI Insights — 5-step pipeline
│   │   ├── html_dashboard.py   # AI BI Dashboard — multi-call generation
│   │   ├── nl_query.py         # NL → pandas → result
│   │   ├── ml.py               # ML model recommender
│   │   ├── cleaning.py         # Automated data cleaning
│   │   ├── report.py           # PDF report generation
│   │   ├── observatory.py      # Usage tracking + latency monitoring
│   │   └── export.py           # CSV export
│   ├── utils/
│   │   ├── domain_mapper.py    # Fuzzy column → semantic role matching
│   │   ├── business_questions.py # Domain-specific chart question library
│   │   └── chart_planner.py    # Smart chart plan builder
│   ├── llm/
│   │   ├── client_factory.py   # Triple LLM routing (Groq/Gemini/Ollama)
│   │   ├── groq_client.py
│   │   ├── gemini_client.py
│   │   └── ollama_client.py
│   ├── rag/                    # RAG pipeline (Supabase pgvector / ChromaDB)
│   ├── session_store.py        # Redis / in-memory session management
│   ├── main.py                 # FastAPI entry point
│   └── requirements_backend.txt
├── frontend/
│   ├── app/
│   │   └── dashboard/
│   │       ├── eda/            # Smart EDA page
│   │       ├── insights/       # Data Insights page
│   │       ├── bi/             # AI BI Dashboard page
│   │       ├── query/          # NL Query page
│   │       ├── ml/             # ML Recommender page
│   │       ├── cleaning/       # Data Cleaning page
│   │       ├── report/         # Report Generator page
│   │       └── observatory/    # Observatory page
│   ├── components/
│   │   └── Sidebar.tsx         # Navigation
│   ├── lib/
│   │   ├── api.ts              # Unified API client (Axios)
│   │   └── store.tsx           # React Context state management
│   └── package.json
├── docker-compose.yml
└── start.sh
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14 (App Router), React, Tailwind CSS, ShadcnUI |
| **Backend** | FastAPI, Python 3.10, Pydantic |
| **Core LLM Providers** | Groq (Llama 3.3-70B), Gemini (2.0-flash), Ollama (local) |
| **BI Dashboard LLMs** | NVIDIA NIM — Kimi K2.6, GLM-5.1, GLM-4.7, Llama 4 Maverick |
| **Chart Generation** | Chart.js 4.4 (via CDN, rendered in sandboxed iframe) |
| **Data Visualization** | Plotly.js, ECharts, Recharts (Insights page) |
| **Session Storage** | Redis (production) / In-memory dict (local) |
| **Vector Store** | Supabase pgvector (primary) / ChromaDB (fallback) |
| **Data Processing** | Pandas, NumPy, scikit-learn |
| **Testing** | Pytest, unittest.mock |

---

## 📈 Platform Capabilities

- ✅ **Zero coding required** — upload CSV/Excel and click through modules
- ✅ **Domain-aware analysis** — telecom, retail, finance, HR, marketing, healthcare, logistics
- ✅ **Business-relevant charts** — every chart answers a specific business question
- ✅ **Insights → BI pipeline** — insights results feed directly into dashboard generation
- ✅ **Production-grade dashboards** — downloadable standalone HTML, Power BI aesthetic
- ✅ **Multi-model failover** — platform never goes down due to single LLM rate limits
- ✅ **167/167 tests passing** — reliable across all modules
- ✅ **Session persistence** — EDA results reused by Insights, Insights reused by BI Dashboard

---

## 🔄 Recommended Workflow

```
1. Upload Dataset
       ↓
2. Smart EDA         → understand data structure
       ↓
3. Data Cleaning     → handle missing values, outliers
       ↓
4. Data Insights     → domain detection, KPIs, business charts
       ↓
5. AI BI Dashboard   → generates using Insights output (fastest + best quality)
       ↓
6. NL Query          → ask follow-up questions
       ↓
7. ML Recommender    → get model recommendations
       ↓
8. Report Generator  → export full PDF report
```

Running **Data Insights before AI BI Dashboard** gives the best dashboard quality — the chart planner reuses pre-computed domain detection, KPIs, and business-relevant chart specs directly from the Insights session cache.

---

## 🌐 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ Primary | Core LLM for EDA, NL Query, Insights |
| `GEMINI_API_KEY` | Secondary | Fallback LLM when Groq rate-limited |
| `NVIDIA_NIM_API_KEY` | ✅ For BI | Required for AI BI Dashboard generation |
| `REDIS_URL` | Optional | Distributed session storage (falls back to in-memory) |
| `SUPABASE_URL` | Optional | Remote vector + metadata storage |
| `SUPABASE_KEY` | Optional | Supabase authentication key |
| `FRONTEND_URL` | App | CORS origin for backend middleware |

Get your **free NVIDIA NIM API key** at [build.nvidia.com](https://build.nvidia.com) — no credit card required, no expiry.

---

## 👤 Author

**Rajat Thakral**
- 🌐 [rajatthakral.vercel.app](https://rajatthakral.vercel.app)
- 💼 [LinkedIn](https://linkedin.com/in/rajat-thakral-067548204)
- 📧 2004rajatthakral@gmail.com

---

<p align="center">
  <i>If this project helped you, give it a ⭐ — it keeps me building!</i>
</p>
