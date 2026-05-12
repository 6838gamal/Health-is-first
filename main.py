"""
Entry point for Health is First system.
Run: python main.py
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import subprocess
from pathlib import Path


def create_dirs():
    dirs = ["media/videos", "media/audio", "media/thumbnails", "media/broll", "logs"]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


async def setup_database():
    from app.db.base import init_db, AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.models.content_source import ContentSource, SourceType
    from app.core.security import get_password_hash
    from sqlalchemy import select

    try:
        await init_db()
        print("Database tables created")

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == "admin@healthisfirst.com"))
            if not result.scalar_one_or_none():
                admin = User(
                    email="admin@healthisfirst.com",
                    username="admin",
                    hashed_password=get_password_hash("Admin@12345"),
                    full_name="System Administrator",
                    role=UserRole.admin,
                    is_active=True,
                    is_verified=True,
                )
                session.add(admin)

                sources_data = [
                    ("WHO News", "https://www.who.int/rss-feeds/news-english.xml", SourceType.rss, 9.5),
                    ("Medical News Today", "https://www.medicalnewstoday.com/rss", SourceType.rss, 8.0),
                    ("Harvard Health", "https://www.health.harvard.edu/blog/feed", SourceType.rss, 9.0),
                    ("NIH News", "https://www.nih.gov/news-events/news-releases/feed.xml", SourceType.rss, 9.5),
                    ("Healthline", "https://www.healthline.com/rss/health-news", SourceType.rss, 8.0),
                    ("Reddit Health", "https://reddit.com/r/health", SourceType.reddit, 6.0),
                    ("Google Trends", "https://trends.google.com", SourceType.google_trends, 8.5),
                ]
                for name, url, stype, score in sources_data:
                    ex = await session.execute(select(ContentSource).where(ContentSource.url == url))
                    if not ex.scalar_one_or_none():
                        session.add(ContentSource(name=name, url=url, source_type=stype, reliability_score=score))

                await session.commit()
                print("Default admin and content sources seeded")
    except Exception as e:
        print(f"Database setup skipped: {e}")


def run_server():
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    print("Health is First - Autonomous AI Content System")

    create_dirs()
    asyncio.run(setup_database())

    print(f"Starting server...")
    run_server()
