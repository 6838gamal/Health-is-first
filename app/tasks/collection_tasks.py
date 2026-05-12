import logging
from datetime import datetime
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


async def _save_trends_from_items(items: list, source_type: str) -> int:
    from app.db.base import AsyncSessionLocal
    from app.models.trend import Trend
    saved = 0
    async with AsyncSessionLocal() as session:
        for item in items:
            title = item.get("title", "").strip()
            if not title:
                continue
            trend = Trend(
                title=title,
                summary=item.get("summary", "")[:1000],
                source_url=item.get("source_url") or item.get("url", ""),
                trend_score=float(item.get("trend_score", 0.5)),
                quality_score=float(item.get("reliability_score", 5.0)) / 10,
                category=item.get("category", "general"),
                language="ar",
                raw_data=item,
            )
            session.add(trend)
            saved += 1
        await session.commit()
    return saved


def _collect_rss_sync():
    from app.services.data_collection.rss_collector import RSSCollector
    collector = RSSCollector()
    items = collector.fetch_all_feeds()
    saved = run_async(_save_trends_from_items(items, source_type="rss"))
    logger.info(f"RSS collection complete: {saved} trends saved")
    return {"status": "success", "saved": saved}


def _collect_trends_sync():
    from app.services.data_collection.trend_collector import TrendCollector
    collector = TrendCollector()
    trends = collector.collect_all_trends()
    saved = run_async(_save_trends_from_items(trends, source_type="trends"))
    logger.info(f"Trend collection complete: {saved} trends saved")
    return {"status": "success", "saved": saved}


if CELERY_AVAILABLE and celery_app:
    @celery_app.task(bind=True, name="app.tasks.collection_tasks.collect_rss_feeds", max_retries=3)
    def collect_rss_feeds(self):
        try:
            return _collect_rss_sync()
        except Exception as exc:
            logger.error(f"RSS collection failed: {exc}")
            raise self.retry(exc=exc, countdown=300)

    @celery_app.task(bind=True, name="app.tasks.collection_tasks.collect_all_trends", max_retries=3)
    def collect_all_trends(self):
        try:
            return _collect_trends_sync()
        except Exception as exc:
            logger.error(f"Trend collection failed: {exc}")
            raise self.retry(exc=exc, countdown=300)
else:
    # Stub functions when Celery is not available
    class _MockTask:
        def __init__(self, func):
            self.func = func
        def delay(self, *args, **kwargs):
            import threading
            t = threading.Thread(target=self.func, args=args, kwargs=kwargs, daemon=True)
            t.start()
            return type("Result", (), {"id": "local-task"})()

    collect_rss_feeds = _MockTask(_collect_rss_sync)
    collect_all_trends = _MockTask(_collect_trends_sync)
