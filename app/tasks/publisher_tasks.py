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


async def _upload_async(video_id: str, queue_id: str) -> dict:
    from app.db.base import AsyncSessionLocal
    from app.models.video import Video, VideoStatus
    from app.models.publishing_queue import PublishingQueue, QueueStatus
    from app.services.publisher.youtube_service import YouTubeService
    from sqlalchemy import select

    youtube = YouTubeService()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).where(Video.id == video_id))
        video = result.scalar_one_or_none()
        if not video:
            return {"error": "Video not found"}
        q_result = await session.execute(select(PublishingQueue).where(PublishingQueue.id == queue_id))
        queue = q_result.scalar_one_or_none()

        try:
            video.status = VideoStatus.uploading
            if queue:
                queue.status = QueueStatus.uploading
            await session.flush()

            tags = [t.strip("#") for t in (video.tags or "").split() if t.startswith("#")]
            tags.extend(["health", "صحة", "shorts"])

            scheduled_at = None
            if queue and queue.scheduled_at:
                scheduled_at = queue.scheduled_at.isoformat()

            thumbnail_path = None
            if video.thumbnail_id:
                from app.models.thumbnail import Thumbnail
                tr = await session.execute(select(Thumbnail).where(Thumbnail.id == video.thumbnail_id))
                thumb = tr.scalar_one_or_none()
                if thumb:
                    thumbnail_path = thumb.file_path

            response = youtube.upload_video(
                video_path=video.file_path,
                title=video.title,
                description=video.description or "",
                tags=list(set(tags)),
                thumbnail_path=thumbnail_path,
                scheduled_at=scheduled_at,
                category_id=video.category_id,
                is_shorts=video.is_shorts,
            )

            video.youtube_video_id = response["video_id"]
            video.youtube_url = response["url"]
            video.status = VideoStatus.published
            video.published_at = datetime.now(timezone.utc).isoformat()
            if queue:
                queue.status = QueueStatus.published
                queue.published_at = datetime.now(timezone.utc)
                queue.youtube_response = response
            await session.commit()
            return {"status": "success", "youtube_url": response["url"]}
        except Exception as e:
            video.status = VideoStatus.failed
            video.error_message = str(e)
            if queue:
                queue.status = QueueStatus.failed
                queue.error_message = str(e)
                queue.retry_count = (queue.retry_count or 0) + 1
            await session.commit()
            raise


def _upload_sync(video_id: str, queue_id: str):
    return run_async(_upload_async(video_id, queue_id))


if CELERY_AVAILABLE and celery_app:
    @celery_app.task(bind=True, name="app.tasks.publisher_tasks.upload_video_youtube", max_retries=3)
    def upload_video_youtube(self, video_id: str, queue_id: str):
        try:
            return _upload_sync(video_id, queue_id)
        except Exception as exc:
            logger.error(f"YouTube upload failed: {exc}")
            raise self.retry(exc=exc, countdown=600)
else:
    class _MockTask:
        def __init__(self, func):
            self.func = func
        def delay(self, *args, **kwargs):
            import threading
            t = threading.Thread(target=lambda: self.func(*args, **kwargs), daemon=True)
            t.start()
            return type("Result", (), {"id": "local-task"})()

    upload_video_youtube = _MockTask(_upload_sync)
