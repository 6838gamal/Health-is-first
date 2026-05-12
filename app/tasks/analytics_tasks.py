import logging
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from app.tasks.celery_app import celery_app, CELERY_AVAILABLE
except ImportError:
    celery_app = None
    CELERY_AVAILABLE = False


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _sync_analytics_async() -> dict:
    from app.db.base import AsyncSessionLocal
    from app.models.video import Video, VideoStatus
    from app.models.analytics import Analytics
    from app.services.publisher.youtube_service import YouTubeService
    from sqlalchemy import select

    youtube = YouTubeService()
    synced = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Video).where(Video.status == VideoStatus.published, Video.youtube_video_id.isnot(None))
        )
        videos = result.scalars().all()
        for video in videos:
            try:
                stats = youtube.get_video_stats(video.youtube_video_id)
                if not stats:
                    continue
                analytics = Analytics(
                    video_id=video.id, youtube_video_id=video.youtube_video_id,
                    fetch_date=datetime.now(timezone.utc),
                    views=stats.get("views", 0), likes=stats.get("likes", 0),
                    comments=stats.get("comments", 0),
                )
                session.add(analytics)
                synced += 1
            except Exception as e:
                logger.error(f"Failed to sync analytics for {video.youtube_video_id}: {e}")
        await session.commit()
    return {"status": "success", "synced": synced}


def _sync_analytics_sync():
    return run_async(_sync_analytics_async())


if CELERY_AVAILABLE and celery_app:
    @celery_app.task(bind=True, name="app.tasks.analytics_tasks.sync_all_analytics", max_retries=3)
    def sync_all_analytics(self):
        try:
            return _sync_analytics_sync()
        except Exception as exc:
            logger.error(f"Analytics sync failed: {exc}")
            raise self.retry(exc=exc, countdown=1800)
else:
    class _MockTask:
        def __init__(self, func):
            self.func = func
        def delay(self, *args, **kwargs):
            import threading
            t = threading.Thread(target=self.func, daemon=True)
            t.start()
            return type("Result", (), {"id": "local-task"})()

    sync_all_analytics = _MockTask(_sync_analytics_sync)
