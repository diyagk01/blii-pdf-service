#!/bin/bash
# Start Docling PDF Extraction Service

echo "🚀 Starting Docling PDF Extraction Service..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    exit 1
fi

# Install requirements
echo "📦 Installing requirements..."
pip3 install -r requirements.txt

# Start the service
echo "🔄 Starting Docling service on port 8080..."
python3 docling_service.py

echo "✅ Docling service started successfully!"
echo "📍 Service running at: http://localhost:8080"
echo "🩺 Health check: http://localhost:8080/health"
