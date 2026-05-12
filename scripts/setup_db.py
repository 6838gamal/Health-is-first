"""
Initial database setup script.
Creates all tables and seeds a default admin user.
Run: python scripts/setup_db.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import init_db, AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.content_source import ContentSource, SourceType
from app.core.security import get_password_hash
from sqlalchemy import select


async def seed_data():
    async with AsyncSessionLocal() as session:
        # Create admin user
        existing = await session.execute(select(User).where(User.email == "admin@healthisfirst.com"))
        if not existing.scalar_one_or_none():
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
            print("✅ Admin user created: admin@healthisfirst.com / Admin@12345")

        # Seed content sources
        sources = [
            ContentSource(name="WHO News", url="https://www.who.int/rss-feeds/news-english.xml",
                         source_type=SourceType.rss, reliability_score=9.5, category="global_health"),
            ContentSource(name="Medical News Today", url="https://www.medicalnewstoday.com/rss",
                         source_type=SourceType.rss, reliability_score=8.0, category="medical"),
            ContentSource(name="Harvard Health Blog", url="https://www.health.harvard.edu/blog/feed",
                         source_type=SourceType.rss, reliability_score=9.0, category="wellness"),
            ContentSource(name="NIH News", url="https://www.nih.gov/news-events/news-releases/feed.xml",
                         source_type=SourceType.rss, reliability_score=9.5, category="research"),
            ContentSource(name="Healthline", url="https://www.healthline.com/rss/health-news",
                         source_type=SourceType.rss, reliability_score=8.0, category="wellness"),
            ContentSource(name="Reddit Health", url="https://www.reddit.com/r/health/hot.json",
                         source_type=SourceType.reddit, reliability_score=6.0, category="community"),
            ContentSource(name="Google Trends Health", url="https://trends.google.com",
                         source_type=SourceType.google_trends, reliability_score=8.5, category="trending"),
        ]
        for src in sources:
            existing_src = await session.execute(
                select(ContentSource).where(ContentSource.url == src.url)
            )
            if not existing_src.scalar_one_or_none():
                session.add(src)
                print(f"✅ Source added: {src.name}")

        await session.commit()
        print("\n✅ Database seeded successfully!")


async def main():
    print("🚀 Initializing Health is First database...")
    await init_db()
    print("✅ Tables created successfully!")
    await seed_data()
    print("\n🎉 Setup complete! You can now run the app.")
    print("📌 Login credentials: admin@healthisfirst.com / Admin@12345")


if __name__ == "__main__":
    asyncio.run(main())
