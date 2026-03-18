import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env from multiple possible locations
env_loaded = False
possible_env_paths = [
    os.path.join(os.path.dirname(__file__), '.env'),
    os.path.join(os.path.dirname(__file__), '..', '.env'),
]
for env_path in possible_env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Loaded .env from: {env_path}")
        env_loaded = True
        break

if not env_loaded:
    print("WARNING: No .env file found in any location")

# Safely inject Streamlit app path into Python Path
# so we can import modules/ and other shared code.
_streamlit_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'streamlit'))
if _streamlit_path not in sys.path:
    sys.path.insert(0, _streamlit_path)

from routers import upload, eda, cleaning, ml, insights, nl_query, report, observatory, query_clusters

app = FastAPI(title="AI Data Platform Backend")

# Setup CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Healthcheck
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Mount standard routers
app.include_router(upload.router, prefix="/api")
app.include_router(eda.router, prefix="/api")
app.include_router(cleaning.router, prefix="/api")
app.include_router(ml.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(nl_query.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(observatory.router, prefix="/api")
app.include_router(query_clusters.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    print("Backend application starting up...")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("WARNING: GROQ_API_KEY environment variable is not set. Components will fail.")
