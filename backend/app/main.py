import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.database import engine, Base
from backend.app.models import entities
from backend.app.api.v1 import api_v1_router
from backend.app.routers import hiring as legacy_hiring, approvals as legacy_approvals

# Auto-create all relational tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Michelle HR — Enterprise All-in-One AI Agent",
    description="MSc Data Science Master's Thesis Platform covering 7 Core HR Pillars with strict Human-in-the-Loop governance.",
    version="2.0.0"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Unified MSc API v1
app.include_router(api_v1_router)

# Mount Legacy routes for web UI backward compatibility
app.include_router(legacy_hiring.router)
app.include_router(legacy_approvals.router)

# Mount Static Frontend
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def serve_index():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"status": "online", "message": "Michelle HR API v2 is active."}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Michelle HR Enterprise Agent",
        "pillars_active": 7,
        "hitl_enforced": True
    }
