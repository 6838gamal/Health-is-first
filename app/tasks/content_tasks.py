import logging
import asyncio

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


async def _generate_ideas_async(limit: int) -> dict:
    from app.db.base import AsyncSessionLocal
    from app.models.trend import Trend
    from app.models.content_idea import ContentIdea, IdeaStatus
    from app.services.ai.gemini_service import GeminiService
    from sqlalchemy import select, and_

    gemini = GeminiService()
    generated = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Trend)
            .where(and_(Trend.is_processed == False, Trend.is_duplicate == False))
            .order_by(Trend.trend_score.desc())
            .limit(limit)
        )
        trends = result.scalars().all()
        for trend in trends:
            try:
                analysis = gemini.analyze_trend(trend.title, trend.summary or "")
                if not analysis.get("is_safe", True):
                    trend.is_processed = True
                    continue
                idea_data = gemini.generate_content_idea(trend.title, analysis)
                idea = ContentIdea(
                    title=idea_data.get("title", trend.title),
                    hook=idea_data.get("hook", ""),
                    angle=idea_data.get("angle", ""),
                    target_keywords=idea_data.get("target_keywords", []),
                    category=analysis.get("category", "health"),
                    estimated_virality=float(idea_data.get("estimated_virality", 5.0)),
                    status=IdeaStatus.pending,
                    trend_id=trend.id,
                    ai_analysis={"analysis": analysis, "idea": idea_data},
                    safety_check_passed=analysis.get("is_safe", False),
                )
                session.add(idea)
                trend.is_processed = True
                generated += 1
            except Exception as e:
                logger.error(f"Error processing trend {trend.id}: {e}")
                trend.is_processed = True
        await session.commit()
    return {"status": "success", "ideas_generated": generated}


async def _generate_script_async(idea_id: str) -> dict:
    from app.db.base import AsyncSessionLocal
    from app.models.content_idea import ContentIdea, IdeaStatus
    from app.models.script import Script, ScriptStatus
    from app.services.ai.gemini_service import GeminiService
    from sqlalchemy import select

    gemini = GeminiService()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ContentIdea).where(ContentIdea.id == idea_id))
        idea = result.scalar_one_or_none()
        if not idea:
            return {"error": "Idea not found"}
        idea_dict = {"title": idea.title, "hook": idea.hook, "angle": idea.angle, "keywords": idea.target_keywords}
        script_data = gemini.generate_script(idea_dict)
        safety = gemini.safety_check(script_data.get("full_script", ""))
        script = Script(
            content_idea_id=idea.id,
            title=script_data.get("title", idea.title),
            hook=script_data.get("hook", ""),
            body=script_data.get("body", ""),
            cta=script_data.get("cta", ""),
            full_script=script_data.get("full_script", ""),
            description=script_data.get("description", ""),
            hashtags=script_data.get("hashtags", ""),
            estimated_duration=script_data.get("estimated_duration", 45),
            word_count=script_data.get("word_count", 100),
            language="ar",
            status=ScriptStatus.review if safety.get("approved") else ScriptStatus.draft,
            safety_approved=safety.get("approved", False),
            ai_model_used="gemini",
            generation_metadata={"script": script_data, "safety": safety},
        )
        session.add(script)
        idea.status = IdeaStatus.in_production
        await session.commit()
        return {"status": "success", "script_id": str(script.id)}


def _generate_ideas_sync(limit: int = 10):
    return run_async(_generate_ideas_async(limit))


def _generate_script_sync(idea_id: str):
    return run_async(_generate_script_async(idea_id))


if CELERY_AVAILABLE and celery_app:
    @celery_app.task(bind=True, name="app.tasks.content_tasks.generate_content_ideas_batch", max_retries=3)
    def generate_content_ideas_batch(self, limit: int = 10):
        try:
            return _generate_ideas_sync(limit)
        except Exception as exc:
            logger.error(f"Idea generation failed: {exc}")
            raise self.retry(exc=exc, countdown=600)

    @celery_app.task(bind=True, name="app.tasks.content_tasks.generate_script", max_retries=3)
    def generate_script(self, idea_id: str):
        try:
            return _generate_script_sync(idea_id)
        except Exception as exc:
            logger.error(f"Script generation failed: {exc}")
            raise self.retry(exc=exc, countdown=300)
else:
    class _MockTask:
        def __init__(self, func):
            self.func = func
        def delay(self, *args, **kwargs):
            import threading
            t = threading.Thread(target=lambda: self.func(*args, **kwargs), daemon=True)
            t.start()
            return type("Result", (), {"id": "local-task"})()

    generate_content_ideas_batch = _MockTask(_generate_ideas_sync)
    generate_script = _MockTask(_generate_script_sync)
