from pydantic_settings import BaseSettings
from typing import Optional, List
import secrets
import os

# إذا وُجد EXTERNAL_DATABASE_URL يأخذ الأولوية — نكتب فوق DATABASE_URL مباشرة
if os.environ.get("EXTERNAL_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["EXTERNAL_DATABASE_URL"]

_db_url = os.environ.get("DATABASE_URL", "postgresql://localhost/health_is_first")


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Health is First"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = secrets.token_urlsafe(32)
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = _db_url
    DATABASE_SYNC_URL: str = _db_url

    @property
    def async_db_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://") and "+asyncpg" not in url:
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        if "?sslmode=" in url:
            url = url.split("?sslmode=")[0]
        return url

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # JWT
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # YouTube API
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REFRESH_TOKEN: str = ""
    YOUTUBE_CHANNEL_ID: str = ""

    # TTS
    TTS_PROVIDER: str = "edge_tts"
    TTS_VOICE: str = "ar-EG-ShakirNeural"
    TTS_LANGUAGE: str = "ar"

    # Media Paths
    MEDIA_DIR: str = "media"
    VIDEOS_DIR: str = "media/videos"
    AUDIO_DIR: str = "media/audio"
    THUMBNAILS_DIR: str = "media/thumbnails"
    BROLL_DIR: str = "media/broll"

    # Video Settings
    VIDEO_WIDTH: int = 1080
    VIDEO_HEIGHT: int = 1920
    VIDEO_FPS: int = 30
    VIDEO_DURATION_MIN: int = 30
    VIDEO_DURATION_MAX: int = 60

    # Content
    CONTENT_LANGUAGE: str = "ar"
    CHANNEL_NAME: str = "Health is First"
    CHANNEL_NICHE: str = "health and wellness"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Scheduler
    COLLECT_TRENDS_INTERVAL: int = 3600
    GENERATE_CONTENT_INTERVAL: int = 7200

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
