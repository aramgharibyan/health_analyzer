# Health Analyzer

A comprehensive personal health data aggregation and AI analysis platform that connects to **Whoop, Yazio, Renpho, Withings, Braun, Larq, and Fitbod**.

## Features

- **7 Health Platform Integrations** via real APIs (OAuth2 + fallback CSV import)
- **AI Health Assistant** powered by Claude — correlates sleep, nutrition, workouts, and more
- **Lab Test Upload** — upload PDF/image lab results, AI extracts and interprets biomarkers
- **Unified Dashboard** — charts for sleep, HRV, weight, activity over time
- **Daily AI Insights** — proactive analysis identifying cross-metric correlations

## Quick Start

### 1. Configure environment
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
```

### 2. Run with Docker
```bash
docker-compose up --build
```
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/api/docs

### 3. Run locally (development)

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Integration Setup

### Whoop
1. Create app at https://developer.whoop.com
2. Set redirect URI to `http://localhost:8000/api/integrations/whoop/callback`
3. Add `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET` to `.env`

### Withings
1. Create app at https://developer.withings.com
2. Set redirect URI to `http://localhost:8000/api/integrations/withings/callback`
3. Add `WITHINGS_CLIENT_ID` and `WITHINGS_CLIENT_SECRET` to `.env`

### Fitbod
- OAuth2 or use **Import CSV** (Settings > Export Workout Data in Fitbod app)

### Yazio
- OAuth2 (partner API) or use **Import CSV** (Profile > Export Data in Yazio app)

### Renpho
- Connect via email/password (uses Renpho's internal API)
- Or use **Import CSV** (Profile > More > Export Data in Renpho app)

### Braun
- Connect via API key (partner portal) or use **Manual Entry** / **Import CSV**

### Larq
- OAuth2 or use **Manual Log** for water intake

## AI Assistant

The AI assistant has access to all your health data and can:
- Identify correlations (e.g., "high-carb dinner → worse sleep")
- Answer questions about trends and patterns
- Interpret lab test results in context
- Give personalized recommendations

Requires: `ANTHROPIC_API_KEY` in `.env`

## Tech Stack

- **Backend**: Python FastAPI + SQLAlchemy + SQLite
- **Frontend**: React + TypeScript + Vite + Tailwind CSS + Recharts
- **AI**: Claude claude-opus-4-6 via Anthropic SDK (with prompt caching)
- **Auth**: JWT tokens
