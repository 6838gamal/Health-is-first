import logging
import asyncio
import os

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


async def _video_pipeline_async(script_id: str) -> dict:
    from app.db.base import AsyncSessionLocal
    from app.models.script import Script
    from app.models.video import Video, VideoStatus
    from app.models.thumbnail import Thumbnail, ThumbnailStatus
    from app.services.audio.tts_service import TTSService
    from app.services.video.video_renderer import VideoRenderer
    from app.services.thumbnail.thumbnail_generator import ThumbnailGenerator
    from app.services.ai.gemini_service import GeminiService
    from sqlalchemy import select

    tts = TTSService()
    renderer = VideoRenderer()
    thumb_gen = ThumbnailGenerator()
    gemini = GeminiService()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()
        if not script:
            return {"error": "Script not found"}

        video = Video(
            script_id=script.id, title=script.title,
            description=script.description, status=VideoStatus.generating_audio,
            tags=script.hashtags,
        )
        session.add(video)
        await session.flush()

        try:
            audio_path = tts.generate_audio(script.full_script, output_filename=f"audio_{video.id}.mp3")
            video.audio_path = audio_path
            video.status = VideoStatus.rendering

            prompt_data = gemini.generate_thumbnail_prompt(script.title, script.hook)
            thumbnail_path = thumb_gen.generate_from_prompt_data(prompt_data, script.title)
            thumbnail = Thumbnail(
                script_id=script.id, file_path=thumbnail_path,
                title_text=prompt_data.get("main_text", script.title),
                sub_text=prompt_data.get("sub_text", ""),
                ai_prompt=str(prompt_data), status=ThumbnailStatus.generated,
            )
            session.add(thumbnail)
            await session.flush()
            video.thumbnail_id = thumbnail.id

            video_path = renderer.render_shorts_video(
                script_title=script.title, full_script=script.full_script,
                audio_path=audio_path, output_filename=f"video_{video.id}.mp4",
            )
            video.file_path = video_path
            info = renderer.get_video_info(video_path)
            video.duration = info.get("duration")
            video.file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
            video.status = VideoStatus.review
            await session.commit()
            return {"status": "success", "video_id": str(video.id)}
        except Exception as e:
            video.status = VideoStatus.failed
            video.error_message = str(e)
            await session.commit()
            raise


def _video_pipeline_sync(script_id: str):
    return run_async(_video_pipeline_async(script_id))


if CELERY_AVAILABLE and celery_app:
    @celery_app.task(bind=True, name="app.tasks.video_tasks.create_video_pipeline", max_retries=2)
    def create_video_pipeline(self, script_id: str):
        try:
            return _video_pipeline_sync(script_id)
        except Exception as exc:
            logger.error(f"Video pipeline failed: {exc}")
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

    create_video_pipeline = _MockTask(_video_pipeline_sync)
