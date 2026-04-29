# 📘 AI Data Platform: Comprehensive Project Guide

This document provides a deep dive into the architecture, logic, and structure of the AI Data Platform. It is designed to help developers understand how the system works and how to contribute to it.

---

## 🚀 1. High-Level Overview
The **AI Data Platform** is an end-to-end agentic automation tool that transforms raw tabular data (CSV/Excel) into actionable business insights without requiring the user to write a single line of code.

### The "Decoupled" Evolution
The project recently moved from a Streamlit-based monolithic prototype to a modern **decoupled architecture**:
- **Backend**: FastAPI (Python 3.12)
- **Frontend**: Next.js 14 (React + Tailwind CSS + ShadcnUI)
- **Orchestration**: Docker Compose

---

## 🏗️ 2. System Architecture

The platform follows a classic **client-server** model with a heavy emphasis on **agentic orchestration**.

### A. Frontend (Next.js)
The frontend is a single-page application (SPA) style dashboard. It handles:
- File uploads and state management.
- Dynamic rendering of dataframes and charts.
- Interaction with the 6 core AI modules.
- Session persistence via a global `store`.

### B. Backend (FastAPI)
The backend is the "brain" of the platform. It is designed around modular routers:
- **FastAPI Core**: Handles routing, CORS, and dependency injection.
- **Worker Layer**: Background tasks (via FastAPI `BackgroundTasks`) for long-running processes like generating full reports or indexing RAG databases.
- **Session Store**: In-memory and Redis-backed session management to keep track of uploaded datasets across refreshes.

### C. The Triple LLM Router (The Core Innovation)
The platform uses a custom orchestration layer that intelligently routes prompts:
1. **Primary (Groq/Llama3)**: High speed, low latency.
2. **Secondary (Gemini Pro)**: Larger context window, used if Groq is rate-limited or fails.
3. **Fallback (Ollama/Local)**: Local LLM fallback ensures the platform works even without an internet connection or if API keys expire.

---

## 📁 3. File Structure & Module Map

### `/backend` (The Engine)
- `main.py`: Entry point, initializes FastAPI and includes all routers.
- `routers/`: 
    - `upload.py`: Handles file parsing and initial RAG indexing.
    - `eda.py`: Performs statistical analysis and visualization logic.
    - `nl_query.py`: Converts English questions into Pandas/Code execution.
    - `insights.py`: Generates narrative summaries using LLMs.
    - `ml.py`: Classifies data and recommends ML models.
    - `observatory.py`: Provides audit logs for every LLM call.
- `llm/`: The client factory and provider-specific wrappers (Groq, Gemini, Ollama).
- `rag/`: Logic for chunking data and managing the ChromaDB vector store.
- `utils/`: Reusable helpers for visualization, data cleaning, and validation.

### `/frontend` (The UI)
- `app/`: Next.js App Router structure.
- `components/`: UI components (Sidebar, Charts, DataTables).
- `lib/api.ts`: Centralized Axios client for all backend communication.
- `lib/store.tsx`: React Context for managing the "current dataset" state.

---

## 🛠️ 4. How the Modules Work (The "Magic")

### 1. Smart EDA
Unlike basic chart generators, this module performs:
- **Type Detection**: Distinguishes between categorical, numerical, and datetime data.
- **Statistical Profiling**: Calculates skewness, kurtosis, and correlation matrices.
- **Smart Plotting**: Automatically chooses the best chart type (BoxPlot for outliers, Histograms for distributions, Heatmaps for correlations).

### 2. NL Query Engine
1. User asks: *"Who are the top 5 customers by spend?"*
2. System sends the **Schema** (columns + samples) to the LLM.
3. LLM generates **Python code** (Pandas).
4. System executes code in a sandboxed environment.
5. Returns both the Result and the Visualization.

### 3. RAG Pipeline
When a file is uploaded, the platform doesn't just store it. It:
- Embeds the column metadata and sample rows into **ChromaDB**.
- When you ask a question, it retrieves the most relevant "context" from the file to help the LLM understand the business domain.

---

## 📦 5. Data Flow & Persistence

| Data Type | Storage Method | Purpose |
|-----------|----------------|---------|
| **Datasets** | `uploads_data` volume | Raw CSV/Excel files for analysis |
| **Embeddings** | `chroma_data` volume | Vector search for RAG-based queries |
| **Audit Logs** | `logs_data` (SQLite) | Tracking LLM usage and failover history |
| **State** | Redis | Temporary session storage and rate limiting |

---

## 🛠️ 6. Contributing & Extension

### Adding a New Analysis Module:
1. Create a new router in `backend/routers/`.
2. Register it in `backend/main.py`.
3. Add a new page in `frontend/app/dashboard/` to consume the new API.
4. If it requires LLM logic, use the `LLMClientFactory` to maintain the triple-routing benefit.

### Running for Development:
Use the root `start.sh` script to run both services simultaneously without Docker for faster hot-reloading:
```bash
./start.sh
```

---

*This guide was generated to ensure architectural continuity and ease of onboarding. Keep building!*
