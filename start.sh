#!/bin/bash

# Set default port if not provided
export PORT=${PORT:-8080}

echo "Starting Docling service on port $PORT"

# Start the Docling service with single worker to avoid OOM
exec gunicorn docling_service:app \
    --workers 1 \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --max-requests 100 \
    --max-requests-jitter 10
