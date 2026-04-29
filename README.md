# 🧠 AI-Powered Analytics Platform

<p align="center">
  <b>From raw data → insights, with zero coding required.</b><br/>
  A 6-module agentic automation platform powered by triple LLM routing and automatic failover.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Groq-FF6B35?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge" />
  <img src="https://img.shields.io/badge/RAG_Pipeline-7C3AED?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Tests-167%2F167_Passing-22c55e?style=for-the-badge" />
</p>

---

## 📌 What Is This?

Most data analysis tools require either coding expertise or expensive SaaS subscriptions. This platform eliminates both.

Upload **any tabular dataset** → get automated EDA, natural language querying, LLM-generated insights, and ML recommendations — no code, no setup, no expertise required.

Built for data analysts, product managers, and non-technical decision-makers who need fast, reliable answers from their data.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔁 **Triple LLM Routing** | Groq → Gemini → Ollama with automatic failover — 60% cost reduction |
| 🗣️ **Natural Language Queries** | Ask questions about your data in plain English |
| 🤖 **Smart EDA** | Automated exploratory data analysis — distributions, correlations, outliers |
| 💡 **LLM Insights Engine** | AI-generated narrative summaries of your dataset |
| 🧩 **ML Recommender** | Suggests the right ML model based on your data shape and goal |
| ✅ **167/167 Tests Passing** | Fully tested across all modules |

---

## 🏗️ Architecture

```
  📂 Input Dataset (CSV / Excel)
         │
         ▼
  ┌─────────────────────────────────────────┐
  │          DATA INGESTION LAYER           │
  │    Validation · Cleaning · Profiling    │
  └──────────────────┬──────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  ┌─────────────┐       ┌────────────────┐
  │  Smart EDA  │       │  NL Query      │
  │  Module     │       │  Engine        │
  └─────────────┘       └────────────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
  ┌─────────────────────────────────────────┐
  │         LLM ORCHESTRATION LAYER         │
  │   Groq  ──►  Gemini  ──►  Ollama        │
  │          (automatic failover)           │
  └──────────────────┬──────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  ┌─────────────┐       ┌────────────────┐
  │  LLM        │       │  ML            │
  │  Insights   │       │  Recommender   │
  └─────────────┘       └────────────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
  ┌─────────────────────────────────────────┐
  │            INSIGHT OUTPUT               │
  │   Reports · Visualizations · Actions   │
  └─────────────────────────────────────────┘
```

---

## 🧩 Modules Breakdown

### 1. 📊 Smart EDA
Automated exploratory data analysis — detects data types, distributions, missing values, correlations, and outliers without writing a single line of pandas.

### 2. 🗣️ Natural Language Query Engine
Ask your data anything in plain English:
> *"What's the average revenue by region in Q3?"*
> *"Which customers have the highest churn risk?"*

### 3. 💡 LLM Insights Generator
Passes statistical findings to the LLM layer and returns human-readable narrative insights, anomaly explanations, and trend summaries.

### 4. 🤖 ML Recommender
Analyzes your dataset's shape, target variable type, and class balance — then recommends the optimal ML algorithm and preprocessing steps.

### 5. 🔁 Triple LLM Router
```
Request ──► Groq (primary, fastest)
              │ (if fails/rate-limited)
              ▼
           Gemini (secondary)
              │ (if fails)
              ▼
           Ollama (local fallback, always available)
```
- **60% prompt cost reduction** vs. single-provider setup
- Zero downtime — failover is automatic and invisible to the user

### 6. 🧪 Test Suite
167 tests across all modules ensuring reliability at every layer.

---

## 🚀 Getting Started

### Prerequisites
```bash
Python 3.10+
Groq API Key      # https://console.groq.com
Gemini API Key    # https://aistudio.google.com
Ollama (optional) # https://ollama.ai — for local fallback
```

### Installation
```bash
# Clone the repo
git clone https://github.com/RajatThakral01/ai-analytics-platform.git
cd ai-analytics-platform

# Install and run using Docker (Recommended)
docker-compose up --build -d
# The platform will be available at http://localhost:3000
```

### Configuration
```bash
# Copy the example env file
cp .env.example .env

# Add your API keys
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
OLLAMA_BASE_URL=http://localhost:11434  # optional
```

### Run Locally (Without Docker)
```bash
# We provide a script to start the backend and frontend locally
./start.sh
# Open http://localhost:3000 in your browser
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
ai-analytics-platform/
├── backend/                  # FastAPI Backend Layer
│   ├── routers/              # API Endpoints (EDA, Insights, etc.)
│   ├── llm/                  # Triple LLM routing logic
│   ├── main.py               # API entry point
│   └── requirements_backend.txt
├── frontend/                 # Next.js Application Layer
│   ├── app/                  # App router pages
│   ├── components/           # UI Components
│   └── package.json
├── docker-compose.yml        # Docker configuration
└── start.sh                  # Local execution script
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, React, Tailwind CSS |
| Backend | FastAPI, Python 3.12 |
| LLM Providers | Groq, Gemini, Ollama |
| Orchestration | Custom LLM Router with failover |
| RAG Pipeline | LangChain / Custom RAG |
| Data Processing | Pandas, NumPy |
| Testing | Pytest (167/167) |

---

## 📈 Results

- ✅ **60% reduction** in prompt costs via intelligent LLM routing
- ✅ **167/167 tests** passing across all modules
- ✅ **Zero coding required** for end-to-end data analysis
- ✅ **Automatic failover** — platform never goes down due to LLM rate limits

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
