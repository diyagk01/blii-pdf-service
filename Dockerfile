FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY docling_service.py .

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Set environment variables for memory optimization
ENV PORT=8080 WEB_CONCURRENCY=1

# Start the Docling service with single worker to avoid OOM
CMD gunicorn docling_service:app --workers 1 --bind 0.0.0.0:${PORT} --timeout 120 --max-requests 100 --max-requests-jitter 10
