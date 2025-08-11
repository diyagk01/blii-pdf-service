#!/bin/bash

# Deployment script for Blii PDF Extraction Service
echo "🚀 Deploying Blii PDF Extraction Service..."

# Check if we're in the python-services directory
if [ ! -f "docling_service.py" ]; then
    echo "❌ Error: Please run this script from the python-services directory"
    exit 1
fi

# Option 1: Railway Deployment
echo "📡 Option 1: Deploy to Railway"
echo "1. Install Railway CLI: npm install -g @railway/cli"
echo "2. Login: railway login"
echo "3. Create project: railway new"
echo "4. Deploy: railway up"
echo ""

# Option 2: Render Deployment
echo "🎨 Option 2: Deploy to Render"
echo "1. Push code to GitHub"
echo "2. Connect GitHub repo to Render"
echo "3. Use render.yaml configuration"
echo "4. Deploy automatically"
echo ""

# Option 3: Docker deployment
echo "🐳 Option 3: Docker Deployment"
echo "Building Docker image..."
docker build -t blii-pdf-extraction:latest .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully"
    echo "To run locally: docker run -p 8080:8080 blii-pdf-extraction:latest"
    echo "To deploy to cloud: Push to your container registry"
else
    echo "❌ Docker build failed"
fi

echo ""
echo "🔗 After deployment, update the service URL in:"
echo "   services/enhanced-content-extractor.ts"
echo "   Change 'http://localhost:8080' to your production URL"

echo ""
echo "✅ Deployment configurations ready!"
