from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import get_settings
from app.database import create_tables
from app.api.auth import router as auth_router
from app.api.health_data import router as health_router
from app.api.lab_tests import router as lab_tests_router
from app.api.ai_assistant import router as ai_router
from app.api.integrations_status import router as integrations_status_router
from app.api.integrations import router as integrations_router

settings = get_settings()

app = FastAPI(
    title="Health Analyzer API",
    description="Unified health data aggregation and AI analysis platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    os.makedirs("uploads/lab_tests", exist_ok=True)

# Mount static files for uploads
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Register routers
app.include_router(auth_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(lab_tests_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(integrations_status_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Health Analyzer API", "version": "1.0.0"}


@app.get("/")
def root():
    return {"message": "Health Analyzer API - visit /api/docs for documentation"}
