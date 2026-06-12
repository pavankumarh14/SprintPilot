# Deployment Guide for Render.com (Docker)

## ✅ What's Already Done

1. **Dockerfile** - Multi-stage Docker build for unified deployment
2. **render.yaml** - Render deployment configuration using Docker runtime
3. **Frontend implementations** - All TODO stubs completed
4. **Backend APIs** - All endpoints functional
5. **AI Scenario Planning** - Fully implemented
6. **Static file serving** - Backend configured to serve React SPA

---

## 🐳 Docker Deployment (Recommended)

The application uses a multi-stage Dockerfile that:
1. Builds the React frontend in stage 1
2. Sets up Python backend in stage 2
3. Copies built frontend to be served by FastAPI
4. Runs as a single unified service

### Dockerfile Overview

```dockerfile
# Stage 1: Build React Frontend
FROM node:18-alpine AS frontend-builder
# ... builds frontend/build

# Stage 2: Python Backend + Serve Frontend  
FROM python:3.11-slim
# ... installs Python deps, copies backend + built frontend
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🔑 Required Environment Variables

You **MUST** set these environment variables in the Render dashboard:

### 1. `GEMINI_API_KEY` (Required)
- **Description**: Google Gemini API key for AI features
- **How to get it**:
  1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
  2. Click "Create API Key"
  3. Copy the key
- **Set in Render**: Dashboard → Environment → Add Environment Variable
  - Key: `GEMINI_API_KEY`
  - Value: `your-api-key-here`

### Auto-configured Variables (Already in render.yaml)

These are already configured in `render.yaml` and don't need manual setup:

- `PYTHON_VERSION`: `3.11.0`
- `NODE_ENV`: `production`
- `PORT`: `8000` (Render will override this automatically)

---

## 🚀 Deployment Steps

### Option 1: Deploy via Render Blueprint (Recommended)

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "ready for Docker deployment"
   git push origin main
   ```

2. **Connect to Render**:
   - Go to [render.com](https://render.com)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository: `pavankumarh14/SprintPilot`
   - Render will auto-detect `render.yaml`

3. **Configure Environment Variables**:
   - Before clicking "Apply", add:
     - `GEMINI_API_KEY`: Your Google Gemini API key

4. **Deploy**:
   - Click "Apply"
   - Render will build the Docker image and deploy
   - Build time: ~5-10 minutes (first build)

### Option 2: Manual Web Service Creation

1. **Create New Web Service**:
   - Dashboard → "New" → "Web Service"
   - Connect your GitHub repo

2. **Configure Service**:
   - **Name**: `sprintpilot`
   - **Runtime**: Docker
   - **Dockerfile Path**: `./Dockerfile`
   - **Plan**: Free

3. **Set Environment Variables**:
   - Add `GEMINI_API_KEY`

4. **Deploy**:
   - Click "Create Web Service"

---

## 📋 Post-Deployment Checklist

- [ ] Service status shows "Live" in Render dashboard
- [ ] Health check endpoint responding: `https://your-app.onrender.com/api/health`
- [ ] Frontend loads correctly at root URL
- [ ] AI features work (test scenario planning)
- [ ] All API endpoints accessible under `/api/*`

---

## 🧪 Testing Your Deployment

### Health Check
```bash
curl https://your-app.onrender.com/api/health
# Should return: {"status":"ok","service":"SprintPilot API"}
```

### LLM Status Check
```bash
curl https://your-app.onrender.com/api/llm-status
# Should return: {"llm_active":true,"source":"header"}
```

### Frontend
Open `https://your-app.onrender.com` in browser:
- Should see SprintPilot landing page
- Navigate to Board, Forecast, Dependencies, Scenarios pages
- Test drag-and-drop on Board page
- Generate AI scenarios

---

## 🔧 Troubleshooting

### Build Fails
- Check Render logs for specific error
- Verify all dependencies in `package.json` and `requirements.txt`
- Ensure Dockerfile syntax is correct

### Frontend Not Loading
- Check if `frontend/build` directory exists in Docker image
- Verify `main.py` has static file serving code
- Check browser console for errors

### API Errors
- Verify `GEMINI_API_KEY` is set correctly
- Check Render logs: Dashboard → Logs
- Test individual endpoints

### Performance Issues on Free Tier
- Free tier sleeps after 15 min inactivity
- First request after sleep takes ~30s to wake up
- Consider upgrading to paid plan for always-on service

---

## 💰 Cost Considerations

### Free Tier (Current Setup)
- ✅ Single unified service (backend + frontend)
- ✅ 750 hours/month free
- ⚠️ Sleeps after 15 min inactivity
- ⚠️ ~30s cold start
- ✅ Perfect for demos and hackathons

### Paid Plan ($7/month)
- Always-on (no sleep)
- Faster performance
- Custom domain support
- More build minutes

---

## 📝 Local Docker Testing (Optional)

Test the Docker build locally before deploying:

```bash
# Build the Docker image
docker build -t sprintpilot .

# Run the container
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your-key-here \
  sprintpilot

# Access at http://localhost:8000
```

---

## 🎯 Summary

**Quick deployment command**:
```bash
git push origin main  # Push changes
# Then go to render.com → New Blueprint → Connect repo → Add GEMINI_API_KEY → Deploy
```

**Required Environment Variable**:
- `GEMINI_API_KEY` - Get from [Google AI Studio](https://aistudio.google.com/app/apikey)

**Deployment URL**:
- Your app will be available at: `https://sprintpilot.onrender.com` (or custom name)

**Next Steps After Deployment**:
1. Test all features
2. Monitor logs for errors
3. Share your deployed URL!

Good luck with your deployment! 🚀
