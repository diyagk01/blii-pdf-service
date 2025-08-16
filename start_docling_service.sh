#!/bin/bash
# Start Docling PDF Extraction Service

echo "🚀 Starting Docling PDF Extraction Service..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements in virtual environment
echo "📦 Installing requirements..."
python3 -m pip install -r requirements.txt

# Start the service
echo "🔄 Starting Docling service on port 8080..."
python3 docling_service.py

echo "✅ Docling service started successfully!"
echo "📍 Service running at: http://localhost:8080"
echo "🩺 Health check: http://localhost:8080/health"
