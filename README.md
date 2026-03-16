# AI Data Analysis Platform

## Project Structure
- streamlit/ - Original Streamlit app (legacy UI)
- backend/ - FastAPI REST API server
- frontend/ - Next.js web application
- data/ - Sample datasets
- tests/ - Test suite

## Quick Start

### Start Backend
cd backend
source ../venv/bin/activate
uvicorn main:app --reload --port 8000

### Start Frontend
cd frontend
npm run dev

### Start Streamlit (legacy)
cd streamlit
streamlit run app.py

## Tech Stack
- Frontend: Next.js 14, TypeScript, Tailwind CSS, Recharts
- Backend: FastAPI, Python 3.12
- AI: Groq (Llama 3.3 70B), Gemini 2.0 Flash, Ollama
- RAG: ChromaDB + Sentence Transformers
- ML: scikit-learn
