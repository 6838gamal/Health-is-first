import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging import logger
from app.db.base import init_db
from app.api.v1.router import api_router
from app.dashboard.routes import dashboard_router

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Health is First System...")
    os.makedirs(settings.VIDEOS_DIR, exist_ok=True)
    os.makedirs(settings.AUDIO_DIR, exist_ok=True)
    os.makedirs(settings.THUMBNAILS_DIR, exist_ok=True)
    os.makedirs(settings.BROLL_DIR, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    # DB is initialized by main.py startup script before uvicorn starts
    logger.info("Application ready")
    yield
    logger.info("Shutting down Health is First System...")
    from app.db.base import engine
    try:
        await engine.dispose()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Autonomous AI Content System for YouTube Health Channel",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files
    try:
        app.mount("/static", StaticFiles(directory="app/static"), name="static")
        app.mount("/media", StaticFiles(directory="media"), name="media")
    except Exception:
        pass

    # Routers
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    app.include_router(dashboard_router)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    @app.get("/")
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard")

    return app


app = create_app()
