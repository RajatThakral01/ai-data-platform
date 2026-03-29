# Broader Vision, Strategy & Copilot Workflow

---

# PART 1 — The Bigger Picture & Final Goal

## What We're Building (The Vision)

**"The AI Data Analyst that replaces your first hour with a consultant."**

When a business person gets a new dataset, the first hour is always the same:
- What is this data about?
- What columns matter?
- Are there data quality issues?
- What are the key metrics?
- What business questions can this answer?
- Show me the most important charts

Your platform does all of this automatically in 60 seconds. That's the core value.

## What We Are NOT

We are NOT trying to replace Power BI or Tableau. They are complex BI tools requiring data modeling expertise, DAX formulas, IT setup, and hours of dashboard building.

**We are the tool that comes BEFORE Power BI.** We help anyone — with zero data expertise — understand what their data contains, what it means, and what to do with it.

## The Positioning

```
Power BI / Tableau:
"Here are your tools. Now build a dashboard."
→ Requires expertise, hours of work

Your Platform:
"Upload your data. Here's what it means."
→ Zero expertise, 60 seconds
```

## Why This Is Genuinely Novel

1. **NL Query with code execution** — not just keyword search, actually runs Python pandas on your data
2. **Auto domain detection** — telecom/retail/ecommerce — generates relevant KPIs automatically  
3. **Hybrid RAG** — PageIndex + pgvector semantic + keyword search on uploaded data
4. **Query clustering** — HDBSCAN groups similar questions to surface "people also asked"
5. **Auto Metabase dashboard** — AI decides what to visualize, creates the dashboard automatically
6. **Full observability** — every LLM call tracked with latency, fallback rate, cost
7. **All in one** — EDA + cleaning + ML + insights + NL query + PDF report + BI dashboard

No single tool does all of this. Power BI has no NL query. Tableau has no auto insights. Jupyter has no BI dashboard. ChatGPT has no persistent ML training.

## Final Production Goal

```
User journey (what we want):
1. Go to your-platform.vercel.app
2. Upload any CSV (no signup needed)
3. See instant EDA — rows, columns, distributions
4. Get AI insights — "this is telecom churn data, 26.5% churn rate"
5. Ask questions in English — instant answers with business context
6. Click "View BI Dashboard" — Metabase opens with pre-built charts
7. Download PDF report — full analysis in one document
8. All in under 2 minutes, zero expertise required
```

---

# PART 2 — Development Strategy & Mindset

## Core Principles We Follow

### 1. Don't Compete, Differentiate
When we identified that we can't replicate Power BI's chart library, we didn't try. Instead we built something Power BI can't do — auto AI analysis. This thinking applies everywhere. Ask: "what can we do that they can't?" not "how do we copy them?"

### 2. Build for Real Users, Not Evaluators
Every feature decision is made from the perspective of: "if someone with no data background uploaded their sales CSV, would this actually help them?" Not: "will this impress the BTech committee?"

### 3. Fallback Everything
Every external dependency has a fallback:
- Supabase down → Redis cache
- Redis down → in-memory sessions
- Groq API down → Gemini → Ollama
- pgvector not available → ChromaDB
- Metabase unavailable → export button still works

This makes the platform robust without requiring everything to be perfect.

### 4. Don't Over-Engineer
When something works well enough, move on. The NL Query is good enough — we didn't spend 3 days making it perfect. Ship, then improve.

### 5. Test in Docker Before Committing
All changes are tested with `docker-compose up` before pushing to GitHub. This catches environment issues before they become Railway deployment failures.

---

# PART 3 — VS Code + GitHub Copilot Workflow

## Setup
- VS Code with GitHub Copilot (Student Pro plan)
- Claude (this chat) does: planning, architecture, reviewing outputs, debugging
- Copilot does: actual code writing and file editing

## Available Copilot Models

| Model | Cost | Best For |
|---|---|---|
| **Grok Code Fast 1** | 0.25x | Find/replace, simple edits, git commands, single-file fixes |
| **Claude Haiku 4.5** | 0.33x | Single file rewrites, reading files, quick fixes |
| **GPT-5.1** | 1x | General tasks, multi-file reads |
| **GPT-5.2-Codex** | 1x | Building new features, complex rewrites |
| **Gemini 2.5 Pro** | 1x | Reading many files at once, large codebase understanding |

## Token Efficiency Rules

```
Use Grok Code Fast 1 when:
- Repetitive find/replace across files
- Running terminal commands
- Git operations
- Simple one-line fixes
- Adding a single import or variable

Use Claude Haiku 4.5 when:
- Single file surgical edits
- Verifying a file looks correct
- Small function additions

Use Gemini 2.5 Pro when:
- Need to read 3+ files at once before writing anything
- Understanding how existing code connects together
- Auditing before a major refactor

Use GPT-5.2-Codex when:
- Building entirely new features (new routers, new pages)
- Complex rewrites with business logic
- When the feature has multiple interacting parts

Use GPT-5.1 when:
- General questions about how to approach something
- When other models are down or slow
```

## Copilot Modes

- **Ask** — read files, audit code, answer questions. Does NOT edit files.
- **Agent** — edits files, runs terminal commands, creates files. Use for all actual changes.
- **Plan** — creates a step-by-step plan before doing anything. Use for complex multi-file changes.

## Prompt Format We Use

Every Copilot prompt from Claude follows this format:

```
TASK: [what needs to be done]
MODEL: [which model]
MODE: [Agent/Ask/Plan]

PROMPT:
[exact text to paste into Copilot]
```

This format means you can copy-paste directly without confusion.

## Key Copilot Tips We've Learned

1. **Copilot sometimes lies about making changes** — always verify with a follow-up "show me lines X-Y of file" prompt
2. **Docker caches old code** — after Copilot edits, always run `docker-compose build --no-cache [service]` not just restart
3. **Syntax errors in generated code** — Copilot occasionally generates `}` instead of `]`. Verify critical files before rebuilding Docker
4. **File path issues** — Copilot sometimes creates files in wrong directories. Always verify with `ls` or `cat` after creation
5. **When Copilot is offline** — edit files directly in VS Code, changes still take effect in Docker after rebuild

## Standard Verification Pattern

After every Copilot edit, use this to verify:

```
TASK: Verify the change
MODEL: Claude Haiku 4.5
MODE: Ask

PROMPT:
Open [filename] and show me lines [X] to [Y].
Confirm that:
1. [specific thing we wanted] is present
2. [no duplicate imports]
3. [no syntax errors in critical lines]
```

---

# PART 4 — Architecture Decisions (Why We Did What We Did)

## Why FastAPI instead of Django?
FastAPI is async-native, faster, and has automatic OpenAPI docs. For an AI platform with multiple concurrent LLM calls, async matters.

## Why sys.path.insert for streamlit modules?
The streamlit/ folder is the original working app. We don't want to refactor it. Using sys.path lets the FastAPI backend import from it without moving any files. This keeps the "original app untouched" rule.

## Why Redis + Supabase for sessions, not just one?
Redis is fast (in-memory) for active sessions. Supabase is persistent for history. Redis acts as a cache in front of Supabase. This is the standard pattern for session management in production apps.

## Why pgvector instead of ChromaDB?
ChromaDB is great locally but resets when containers restart. pgvector is in Supabase (cloud), survives restarts, and we already have Supabase. One less service to manage.

## Why PageIndex instead of token chunking?
For tabular data (CSV files), arbitrary 512-token chunks break across columns mid-row. PageIndex groups related columns together into semantic "pages" — column groups with stats and sample values. This produces much better RAG retrieval for data questions.

## Why Metabase instead of building charts ourselves?
Building 30 professional chart types with cross-filtering from scratch would take months. Metabase is open source, runs in Docker, connects to our existing Supabase, and gives users a full BI tool. Our job is to tell Metabase what to show — the AI layer is our value, not the chart rendering.

## Why HDBSCAN for query clustering?
HDBSCAN handles variable-density clusters and doesn't require specifying number of clusters upfront. For NL queries, some clusters (aggregation questions) will be dense and some (unique questions) sparse. HDBSCAN handles this better than k-means.

---

# PART 5 — Known Issues & How to Handle Them

## Docker Issues

**"Docker daemon not running"**
→ Open Docker Desktop app first (Cmd+Space → Docker)

**"No changes visible after Copilot edit"**
→ `docker-compose build --no-cache [service] && docker-compose up`

**"Redis exited with code 0"**
→ `docker-compose down && docker-compose up` (Redis occasionally stops gracefully)

**"Frontend build fails with TypeScript errors"**
→ Run `cd frontend && npm run build` locally first to see ALL errors at once, fix them all, then rebuild Docker

## Backend Issues

**"Object of type DataFrame is not JSON serializable"**
→ Always store df as: `df.where(pd.notnull(df), None).to_dict(orient='records')`
→ Always reconstruct: `if isinstance(df, (list, dict)): df = pd.DataFrame(df)`

**"Session or DataFrame not found"**
→ Sessions expire after 2 hours. Upload the file again.

**"Module not found in Docker"**
→ Check that the module is in requirements_backend.txt AND `docker-compose build --no-cache backend`

## Supabase Issues

**"Metabase can't connect to Supabase"**
→ Use Session Pooler connection string (not Direct)
→ Host: `aws-1-ap-south-1.pooler.supabase.com`
→ Port: `5432`
→ Username: `postgres.rhqewolgahcbewrjhzzk`

---

# PART 6 — Deployment Checklist

Before going live on Railway + Vercel:

```
Code Checks:
□ No hardcoded /Users/rajatthakral paths anywhere
□ No hardcoded localhost URLs (use env vars)
□ .env is in .gitignore (check: git status should NOT show .env)
□ All requirements in requirements_backend.txt
□ CORS allows production Vercel domain

Railway Checks:
□ GROQ_API_KEY set
□ GEMINI_API_KEY set
□ SUPABASE_URL set
□ SUPABASE_KEY set
□ REDIS_URL set (from Railway Redis plugin)
□ FRONTEND_URL set (to Vercel URL)
□ health check passes: curl https://railway-url/health

Vercel Checks:
□ NEXT_PUBLIC_API_URL set (to Railway URL)
□ Build succeeds (no TypeScript errors)
□ Upload works end-to-end on live URL
```

---

*Last updated: March 19, 2026*
*This file is for handoff to a new Claude chat session*
