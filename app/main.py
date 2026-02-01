import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import router
from app.api.schemas import HealthResponse
from app.services.scheduler import start_scheduler, stop_scheduler, fetch_usage_data
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting up...")

    start_scheduler(interval_minutes=settings.fetch_interval_minutes)

    await fetch_usage_data()

    yield

    logger.info("Shutting down...")
    stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Baroque - Claude API Usage Leaderboard",
        description="Gamified leaderboard for tracking Claude API usage",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:9000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")

    # Root-level health check (as documented in plan)
    @app.get("/health", response_model=HealthResponse)
    async def root_health_check():
        return HealthResponse(status="healthy", timestamp=datetime.utcnow())

    return app


app = create_app()
