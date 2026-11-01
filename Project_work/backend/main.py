"""FastAPI application entry point for the XAI-OR System."""
import sys
import os
import logging
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import transportation, assignment, history
from database.connection import init_database

logger = logging.getLogger("xai.or")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup if the database is reachable.

    Table creation is best-effort and non-fatal: if MySQL is unavailable the
    app still boots, and solving works (persistence fails gracefully).
    """
    try:
        init_database()
        logger.info("Database tables ensured.")
    except Exception:  # noqa: BLE001 - avoid crashing startup without a DB
        logger.warning("Could not reach database at startup; history endpoints may be unavailable.")
    yield

app = FastAPI(
    title="XAI Operations Research System API",
    description=(
        "Backend API for the Explainable AI Operations Research System. "
        "Provides transportation and assignment problem solving with "
        "step-by-step XAI explanations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for the React frontend (dev server on Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(transportation.router)
app.include_router(assignment.router)
app.include_router(history.router)


@app.get("/api/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "XAI-OR System API",
        "version": "1.0.0",
    }


@app.get("/")
def root() -> dict:
    """Root endpoint with basic info."""
    return {
        "service": "XAI Operations Research System API",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": [
            "POST /api/transportation/solve",
            "POST /api/transportation/explain",
            "POST /api/assignment/solve",
            "POST /api/assignment/explain",
            "GET /api/history/transportation",
            "GET /api/history/assignment",
        ],
    }
