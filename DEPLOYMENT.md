# 🚀 HawkNet-Ai — Deployment Guide

This guide details how to deploy **HawkNet-Ai** to production using **Render.com** (recommended 1-click Blueprint deployment), **Vercel**, or **Docker**.

---

## Option 1: 1-Click Full-Stack Deployment on Render.com (Recommended)

Render natively supports both the Python FastAPI backend and the Vite React static frontend using the included `render.yaml` blueprint.

### Steps:

1. Log in to [Render.com](https://dashboard.render.com/).
2. Click **New +** → **Blueprints**.
3. Connect your GitHub repository: `AdarshVashith/HawkNet-Ai`.
4. Render will automatically detect `render.yaml` and create two services:
   - **`hawknet-ai-backend`** (Python Web Service)
   - **`hawknet-ai-frontend`** (Static Site)
5. Click **Apply**.
6. Once deployed:
   - Copy your Backend API URL (e.g. `https://hawknet-ai-backend.onrender.com`).
   - Go to your Frontend Static Site settings on Render → **Environment Variables** → Add `VITE_API_BASE_URL` with your backend URL.
   - Re-deploy the frontend service.

---

## Option 2: Frontend on Vercel + Backend on Render / Railway

### 1. Backend Deployment (Render or Railway)
- Create a new **Web Service** on Render or Railway pointing to `AdarshVashith/HawkNet-Ai`.
- **Root Directory**: `backend`
- **Build Command**: `pip install --extra-index-url https://download.pytorch.org/whl/cpu torch torchvision && pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `PYTHONPATH`: `.`
  - `APP_NAME`: `HawkNet-Ai`
  - `ENVIRONMENT`: `production`
  - `CORS_ORIGINS`: `*`

### 2. Frontend Deployment (Vercel)
1. Go to [Vercel Dashboard](https://vercel.com/new).
2. Import `AdarshVashith/HawkNet-Ai`.
3. **Framework Preset**: Vite
4. **Root Directory**: `frontend`
5. **Environment Variables**:
   - `VITE_API_BASE_URL`: `https://hawknet-ai-backend.onrender.com`
6. Click **Deploy**.

---

## Option 3: Docker Compose (Self-Hosted Cloud / VPS)

For AWS EC2, DigitalOcean, Hetzner, or local servers:

```bash
# 1. Clone the repository
git clone https://github.com/AdarshVashith/HawkNet-Ai.git
cd HawkNet-Ai

# 2. Build and start services in detached mode
docker compose up --build -d
```

- **Frontend Command Center**: `http://<YOUR-SERVER-IP>:5173`
- **Backend OpenAPI Docs**: `http://<YOUR-SERVER-IP>:8000/docs`
- **Health Endpoint**: `http://<YOUR-SERVER-IP>:8000/health`
