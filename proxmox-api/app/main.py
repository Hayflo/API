"""
ProxAPI - Wrapper FastAPI pour l'API native Proxmox
Authentification JWT propre + toutes les opérations du cycle de vie VM
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.routers import auth, vms

app = FastAPI(
    title="ProxAPI",
    description="Wrapper REST pour piloter Proxmox via son API native",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers API
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(vms.router,  prefix="/api/v1", tags=["VMs"])

# Dashboard statique
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard")
if os.path.isdir(DASHBOARD_DIR):
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")

@app.get("/api/v1/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "ProxAPI"}

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(os.path.join(DASHBOARD_DIR, "index.html"))
