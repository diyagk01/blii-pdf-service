# Deploy Docling Service to Render (RECOMMENDED)

## Why Render is Best for Docling:
- ✅ **Better ML Support**: 512MB RAM on free tier vs Railway's 256MB
- ✅ **More Reliable**: Better Docker support and build stability
- ✅ **Faster Builds**: Typically 3-5 minutes vs Railway's 5-10 minutes
- ✅ **Auto-Deploy**: Connects to GitHub and auto-deploys on push
- ✅ **Free SSL**: Automatic HTTPS certificates

## 🚀 Step-by-Step Deployment:

### 1. Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up/login with GitHub
3. Connect your GitHub account

### 2. Deploy the Service
1. Click **"New +"** → **"Web Service"**
2. Connect repository: `diyagk01/blii-pdf-service` (or your repo)
3. Configure deployment:
   - **Name**: `blii-docling-service`
   - **Root Directory**: `python-services`
   - **Environment**: `Docker`
   - **Plan**: `Free` (to start)
   - **Auto-Deploy**: `Yes`

### 3. Render Will Auto-Detect:
- ✅ Dockerfile (uses our configured Dockerfile)
- ✅ render.yaml (uses our configuration)
- ✅ Health check endpoint (/health)

### 4. Your Service URL:
```
https://blii-docling-service.onrender.com
```

### 5. Update Your App:
Once deployed, update this file in your React Native app:

**File**: `services/content-extractor.ts`
**Line 189**: Change the URL from:
```typescript
const doclingServiceUrl = 'https://blii-pdf-extraction-production.up.railway.app';
```
To:
```typescript
const doclingServiceUrl = 'https://blii-docling-service.onrender.com';
```

---

## 🧪 Test Deployment:

After deployment completes (3-5 minutes):

```bash
# Test health endpoint
curl https://blii-docling-service.onrender.com/health

# Should return:
{
  "status": "healthy",
  "service": "docling_extraction_service",
  "docling_available": true
}

# Run full test
python3 test_actual_docling_service.py
# (Update the service_url in the script first)
```

---

## 🔧 Render Configuration Details:

### Environment Variables (Auto-Set):
- `PORT`: 8080 (Render handles this)
- `PYTHONUNBUFFERED`: 1

### Resource Specs:
- **Free Tier**: 512MB RAM, 0.1 CPU
- **Paid Tier**: 2GB+ RAM, 1+ CPU (if needed)

### Build Process:
1. Render pulls from GitHub
2. Builds Docker image using our Dockerfile
3. Installs Docling and dependencies
4. Starts service with gunicorn
5. Provides public HTTPS URL

---

## 🆚 Render vs Railway Comparison:

| Feature | Render | Railway |
|---------|--------|---------|
| Free RAM | 512MB | 256MB |
| ML Support | ✅ Better | ⚠️ Limited |
| Build Time | 3-5 min | 5-10 min |
| Docker Support | ✅ Native | ✅ Good |
| Auto-Deploy | ✅ Yes | ✅ Yes |
| Custom Domains | ✅ Free | ✅ Free |
| Cold Starts | ~30s | ~20s |

---

## 🎯 Quick Deploy Commands:

If you want to deploy to multiple platforms for redundancy:

```bash
# 1. Render (Manual via dashboard - recommended)
# Use the web interface as described above

# 2. Heroku (if you have Heroku CLI)
cd python-services
heroku create blii-docling-heroku
heroku container:push web
heroku container:release web

# 3. Fly.io (if you have Fly CLI)
cd python-services
fly launch --dockerfile
fly deploy

# 4. DigitalOcean (via dashboard)
# Similar to Render, use their web interface
```

---

## 📱 Update React Native App:

Once your preferred service is deployed, update the service URL:

**File**: `services/content-extractor.ts`
**File**: `services/enhanced-content-extractor.ts`

Find and replace the Railway URL with your new deployment URL.

---

## ✅ Verification Checklist:

- [ ] Service deploys successfully
- [ ] Health endpoint returns correct response
- [ ] PDF upload endpoint works
- [ ] Test script passes all tests
- [ ] React Native app updated with new URL
- [ ] TestFlight users can upload PDFs

**Render is strongly recommended as it has the best track record with ML dependencies like Docling!**
