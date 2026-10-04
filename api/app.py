"""
FastAPI application entry point with lifespan management, CORS, and static dashboard mounting.
"""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes import router
from scheduler.runner import scheduler_service
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("api.app")
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown events."""
    logger.info("Starting WMI System Monitor FastAPI Application...")

    # Start background scheduler if enabled
    if settings.scheduler_enabled:
        scheduler_service.start()

    yield

    # Graceful shutdown
    logger.info("Shutting down WMI System Monitor Application...")
    scheduler_service.stop()


def create_app() -> FastAPI:
    """Builds and configures the FastAPI application."""
    app = FastAPI(
        title="Windows Management Instrumentation (WMI) System Monitor",
        description="Comprehensive system telemetry collector, MongoDB persistence engine, and enterprise dashboard.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Enable CORS for enterprise API consumption
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register REST API endpoints
    app.include_router(router)

    # Ensure static directory exists
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    # Serve static assets
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_dashboard():
        """Serves the interactive web dashboard matching the reference interface."""
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {
            "message": "WMI System Monitor API is online.",
            "docs": "/docs",
            "latest_snapshot": "/api/snapshots/latest",
        }

    return app


# Application singleton for uvicorn
app = create_app()
