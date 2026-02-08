# Production Dockerfile for Railway deployment
FROM python:3.11-slim

# Install system dependencies for chromadb and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model to avoid cold-start downloads
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Create data directories (will be overridden by volume mount in production)
RUN mkdir -p /data/chroma /data/docs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Expose port (Railway sets $PORT)
EXPOSE 8000

# Use Gunicorn with Uvicorn workers for production
# Railway provides $PORT env var
CMD ["sh", "-c", "gunicorn backend.app:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 120 --graceful-timeout 30 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50"]
