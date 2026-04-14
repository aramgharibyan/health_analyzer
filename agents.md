# Health Analyzer — Deployment Agenda

## Status Legend
- [x] Done
- [ ] To do

---

## Phase 1 — Core Application (Done)

- [x] FastAPI backend with JWT authentication
- [x] SQLAlchemy ORM with SQLite (dev) / PostgreSQL (prod)
- [x] React + TypeScript + Tailwind CSS frontend
- [x] Docker Compose dev environment
- [x] Health data models: sleep, activity, nutrition, body metrics, hydration
- [x] AI assistant powered by Claude (with prompt caching)
- [x] Lab test upload, PDF/image parsing, AI-powered result extraction
- [x] Cross-metric correlation analysis and recommendations

## Phase 2 — Integrations (Done)

- [x] Whoop (OAuth2 PKCE) — sleep, recovery, strain, workouts
- [x] Withings (OAuth2) — weight, body composition, blood pressure, sleep
- [x] Fitbod (OAuth2) — strength workouts, volume, muscle groups
- [x] Yazio (OAuth2) — nutrition, calories, macros, meal logging
- [x] Renpho (credentials) — body composition, weight trends
- [x] Braun (API key) — temperature, blood pressure
- [x] Larq (OAuth2) — hydration tracking
- [x] Apple Health export import (ZIP / XML, streaming parser, no OOM)
- [x] Apple Health real-time webhook (Health Auto Export iOS app)

## Phase 3 — Production Readiness (Done)

- [x] Switch from SQLite to PostgreSQL (psycopg2-binary driver)
- [x] PostgreSQL connection pool settings (pool_pre_ping, pool_size, max_overflow)
- [x] Azure Blob Storage for file uploads (lab tests, health exports)
- [x] Dual storage backend: local disk (dev) / Azure Blob (prod)
- [x] Remove unused Celery / Redis dependencies
- [x] Production Dockerfile (no --reload, 2 workers)
- [x] Alembic migrations initialized with autogenerate (11 tables)
- [x] CORS restricted to localhost in non-production environments
- [x] FastAPI lifespan context manager (replaces deprecated on_event)
- [x] Apple Health OOM fix: stream upload to /tmp, parse from disk
- [x] Nginx: client_max_body_size 600m (showstopper for ZIP uploads)
- [x] Nginx: proxy timeouts 600s, security headers, gzip, asset caching
- [x] docker-compose.prod.yml for local smoke-testing (Postgres + Azurite)

---

## Phase 4 — Azure Deployment

### One-Time Azure Setup

- [ ] Create resource group: `az group create --name health-analyzer-rg --location eastus`
- [ ] Create Container Registry (Basic): `az acr create --name healthanalyzerregistry ...`
- [ ] Create PostgreSQL Flexible Server (B1ms, 32 GB)
- [ ] Create Blob Storage account + `health-uploads` container
- [ ] Create Key Vault and store all secrets (see list below)
- [ ] Create Container Apps environment

### Secrets to Store in Key Vault

- [ ] `secret-key` — JWT signing key (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] `anthropic-api-key`
- [ ] `database-url` — full PostgreSQL connection string
- [ ] `azure-storage-connection-string`
- [ ] `whoop-client-id` / `whoop-client-secret`
- [ ] `withings-client-id` / `withings-client-secret`
- [ ] `fitbod-client-id` / `fitbod-client-secret`
- [ ] `yazio-client-id` / `yazio-client-secret`
- [ ] `larq-client-id` / `larq-client-secret`
- [ ] `braun-api-key`

### Backend Deployment

- [ ] Build and push Docker image to ACR: `az acr build --registry healthanalyzerregistry --image health-analyzer-backend:latest ./backend`
- [ ] Deploy Container App (min 0, max 3 replicas, target port 8000)
- [ ] Set all environment variables from Key Vault references
- [ ] Run initial migration: `az containerapp exec ... --command "alembic upgrade head"`
- [ ] Verify: `GET https://<fqdn>/api/health` → `{"status": "healthy"}`

### Frontend Deployment

- [ ] Create Azure Static Web App (Free tier)
- [ ] Connect to GitHub repo, set app-location `/frontend`, output-location `dist`
- [ ] Set `VITE_API_URL` to the Container Apps FQDN in Static Web App config
- [ ] Verify auto-deploy triggers on push to main

### Post-Deployment

- [ ] Update OAuth redirect URIs in each developer dashboard to point at the Container Apps FQDN:
  - Whoop: `https://<fqdn>/api/integrations/whoop/callback`
  - Withings: `https://<fqdn>/api/integrations/withings/callback`
  - Fitbod: `https://<fqdn>/api/integrations/fitbod/callback`
  - Yazio: `https://<fqdn>/api/integrations/yazio/callback`
  - Larq: `https://<fqdn>/api/integrations/larq/callback`
- [ ] Set `FRONTEND_URL` env var in Container App to the Static Web App domain
- [ ] Test end-to-end: register → login → upload lab test → verify AI parsing
- [ ] Test Apple Health ZIP upload (verify no 413, records appear in dashboard)
- [ ] Monitor Container Apps log stream for errors
- [ ] Check PostgreSQL connection count stays below B1ms limit (50 connections)

---

## Estimated Azure Cost

| Service | Tier | Cost/mo |
|---|---|---|
| Container Apps (backend) | Consumption | ~$3–5 |
| Static Web Apps (frontend) | Free | $0 |
| PostgreSQL Flexible Server | B1ms, 32 GB | ~$12–15 |
| Blob Storage | Hot LRS, 10 GB | ~$0.20 |
| Container Registry | Basic | $5 |
| Key Vault | Standard | ~$0.03 |
| DNS Zone | 1 zone | ~$0.50 |
| **Total** | | **~$21–26/mo** |

Well within the $150/mo Azure Enterprise credit.
