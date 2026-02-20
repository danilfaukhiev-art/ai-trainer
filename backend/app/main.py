"""
AI Personal Trainer — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import structlog
import os

from app.core.config import settings
from app.db.base import engine, Base
from app.api.routes import auth, onboarding, workouts, ai_chat, progress, profile, nutrition, reports, subscriptions

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting AI Trainer API", env=settings.app_env)

    # Create tables if not exists
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified")

    yield

    logger.info("Shutting down...")
    await engine.dispose()


app = FastAPI(
    title="AI Personal Trainer API",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")
app.include_router(workouts.router, prefix="/api")
app.include_router(ai_chat.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(nutrition.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")


# Telegram webhook
@app.post("/webhook/telegram")
async def telegram_webhook(request: dict):
    """Handled by python-telegram-bot Application."""
    from bot.app import process_update
    await process_update(request)
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# Serve Mini App static files
STATIC_DIR = "/app/static_miniapp/dist" if os.path.exists("/app/static_miniapp/dist") else "/app/static_miniapp"
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=f"{STATIC_DIR}/assets"), name="assets")

    @app.get("/")
    async def serve_miniapp():
        return FileResponse(f"{STATIC_DIR}/index.html")

    @app.get("/{full_path:path}")
    async def serve_miniapp_routes(full_path: str):
        file_path = f"{STATIC_DIR}/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(f"{STATIC_DIR}/index.html")
