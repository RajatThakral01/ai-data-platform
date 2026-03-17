FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for sentence-transformers and chromadb
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer caching)
COPY backend/requirements_backend.txt .
RUN pip install --no-cache-dir -r requirements_backend.txt

# Copy backend source
COPY backend/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
