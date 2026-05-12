"""
Celery application configuration.
Falls back gracefully if Redis is not available.
"""
try:
    from celery import Celery
    from celery.schedules import crontab
    from app.core.config import settings

    celery_app = Celery(
        "health_is_first",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=[
            "app.tasks.collection_tasks",
            "app.tasks.content_tasks",
            "app.tasks.video_tasks",
            "app.tasks.publisher_tasks",
            "app.tasks.analytics_tasks",
        ],
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Riyadh",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_max_retries=3,
        task_default_retry_delay=60,
        result_expires=86400,
        broker_connection_retry_on_startup=True,
    )

    celery_app.conf.beat_schedule = {
        "collect-trends-hourly": {
            "task": "app.tasks.collection_tasks.collect_all_trends",
            "schedule": crontab(minute=0),
            "options": {"queue": "collection"},
        },
        "collect-rss-every-2h": {
            "task": "app.tasks.collection_tasks.collect_rss_feeds",
            "schedule": crontab(minute=30, hour="*/2"),
            "options": {"queue": "collection"},
        },
        "generate-content-ideas-3x-daily": {
            "task": "app.tasks.content_tasks.generate_content_ideas_batch",
            "schedule": crontab(hour="8,14,20", minute=0),
            "options": {"queue": "content"},
        },
        "sync-analytics-daily": {
            "task": "app.tasks.analytics_tasks.sync_all_analytics",
            "schedule": crontab(hour=6, minute=0),
            "options": {"queue": "analytics"},
        },
    }

    celery_app.conf.task_routes = {
        "app.tasks.collection_tasks.*": {"queue": "collection"},
        "app.tasks.content_tasks.*": {"queue": "content"},
        "app.tasks.video_tasks.*": {"queue": "video"},
        "app.tasks.publisher_tasks.*": {"queue": "publisher"},
        "app.tasks.analytics_tasks.*": {"queue": "analytics"},
    }

    CELERY_AVAILABLE = True

except ImportError:
    import logging
    logging.warning("Celery not available - background tasks disabled")
    celery_app = None
    CELERY_AVAILABLE = False
