# 🧠 AI Data Platform: The Definitive Technical Blueprint

This document is the ultimate reference for the AI Data Platform. It covers the architecture, the "why" behind design decisions, and the internal mechanics of every major module.

---

## 🏗️ 1. Architecture: The Decoupled Stack

The platform is split into two distinct high-performance layers, orchestrated by Docker.

### A. Frontend: The Interaction Layer (Next.js 14)
The frontend is built with **Next.js 14** using the **App Router**. 
- **Styling**: Tailwind CSS for high-fidelity UI; Lucide React for iconography.
- **UI Components**: Built on **ShadcnUI** (Radix UI primitives).
- **State Management**: Uses **React Context API** (`store.tsx`) to track the `currentFileId`, `sessionData`, and `analysisResults` globally.
- **API Communication**: Centralized through `lib/api.ts` using Axios with a predefined `baseURL` and interceptors.

### B. Backend: The Intelligence Layer (FastAPI)
The backend is a **FastAPI** application designed for speed and asynchronous processing.
- **Concurrency**: Leverages Python's `async/await` for LLM calls and `BackgroundTasks` for heavy processing (RAG indexing, Report generation).
- **Session Persistence**: Implemented in `session_store.py`. It uses a **Session-over-File** model where temporary dataframes are cached in memory/Redis to avoid re-reading large files from disk for every module request.

---

## 🤖 2. The Core AI Engine (Agentic Logic)

### A. Triple LLM Routing (Failover & Optimization)
Located in `backend/llm/`, this is the platform's unique selling point.
1. **The Factory**: `client_factory.py` manages a singleton instance of LLM clients.
2. **The Routing Chain**:
   - **Groq (Llama3-70B/8B)**: The primary engine. Blazing fast (<100ms tokens).
   - **Gemini Pro**: The fallback. Higher rate limits and 1M+ context window.
   - **Ollama**: The local safety net. Uses `llama3` or `mistral` locally if the cloud is unreachable.
3. **The Failover Mechanism**: Every LLM call is wrapped in a try-except block that automatically retries with the next provider in the chain, ensuring zero downtime.

### B. RAG (Retrieval-Augmented Generation) Pipeline
Located in `backend/rag/`, this module allows the AI to "know" your data context.
- **Embedder**: Uses `sentence-transformers` (all-MiniLM-L6-v2) to convert column names and sample data into 384-dimensional vectors.
- **Vector Store**: **ChromaDB** stores these embeddings.
- **Context Retrieval**: When a query is made, the system finds the most relevant 5-10 rows or columns to inject into the LLM prompt, providing business context without exceeding token limits.

---

## 📁 3. Modules: Deep Dive

### 1. 📊 Smart EDA (`routers/eda.py`)
- **Automated Profiling**: Detects missing values, unique counts, and cardinality.
- **Visualization Logic**: Uses a helper `visualizations.py` to generate **JSON-serializable chart configs** (Plotly/Recharts compatible) for distributions, scatter plots, and heatmaps.
- **Insights**: Feeds statistical results into the LLM Insights engine to produce "What this means" descriptions.

### 2. 🗣️ NL Query Engine (`routers/nl_query.py`)
This is a "Text-to-Code" engine:
- **Phase 1: Metadata Extraction**: Extracts the schema of the active dataset.
- **Phase 2: Prompt Engineering**: Sends the question + schema to the LLM.
- **Phase 3: Code Execution**: The LLM returns a Python snippet. The backend executes this safely (using `exec()` with specific globals) to produce a `result_df`.
- **Phase 4: Serialization**: Converts the result into a format the frontend can render immediately.

### 3. 🤖 ML Recommender (`routers/ml.py`)
- **Task Identification**: Automatically identifies if the goal is Classification or Regression based on the target variable.
- **Feature Engineering**: Identifies high-cardinality columns and categorical variables that need encoding.
- **Recommendation**: Suggests specific algorithms (XGBoost, Random Forest, etc.) based on dataset size and balance.

### 4. 💡 LLM Insights (`routers/insights.py`)
- **Pattern Recognition**: Specifically designed to find anomalies and correlations.
- **Narrative Generation**: Turns dry numbers into "The business is losing revenue in the East region primarily due to shipping delays."

---

## 📦 4. Data Storage & Persistence

| Component | Storage Type | Details |
|-----------|--------------|---------|
| **Raw Data** | Local Volume (`/app/uploads`) | Temporary storage for uploaded CSV/Excel files. |
| **Vectors** | ChromaDB (`/app/chroma_db`) | Stores embeddings for RAG lookups. |
| **Audit Logs** | SQLite (`llm_logs.db`) | Stores every prompt/response for debugging and monitoring. |
| **Session State** | Redis | Stores user session IDs and active file pointers. |

---

## 🔐 5. Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | **Required**. Primary engine for all modules. |
| `GEMINI_API_KEY` | Secondary engine fallback. |
| `SUPABASE_URL/KEY` | Optional. For long-term user storage. |
| `REDIS_URL` | Redis connection string for session management. |
| `FRONTEND_URL` | URL of the Next.js app (for CORS security). |

---

## 🧪 6. Testing Framework
The platform includes **167 tests** located in `/tests`.
- **Unit Tests**: Test the LLM clients and data loaders in isolation.
- **Integration Tests**: Test the full flow (Upload -> EDA -> Query).
- **Mocking**: Extensive use of `unittest.mock` to simulate LLM responses for CI/CD consistency.

---

## 🛠️ 7. Developer Onboarding
To add a new feature:
1. **Define the Router**: Add a file in `backend/routers/`.
2. **Register**: Add the route to `app.include_router` in `backend/main.py`.
3. **Client**: Use `LLMClientFactory.get_client()` for any AI logic.
4. **UI**: Add a new `.tsx` file in `frontend/app/dashboard/` and a link in `Sidebar.tsx`.

---

*This document is maintained as the ground truth for the AI Data Platform's technical architecture.*
