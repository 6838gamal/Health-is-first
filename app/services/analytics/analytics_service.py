import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.analytics import Analytics
from app.models.video import Video, VideoStatus

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_channel_overview(self) -> Dict:
        total_views = await self.db.execute(select(func.sum(Analytics.views)))
        total_likes = await self.db.execute(select(func.sum(Analytics.likes)))
        total_comments = await self.db.execute(select(func.sum(Analytics.comments)))
        total_videos = await self.db.execute(
            select(func.count(Video.id)).where(Video.status == VideoStatus.published)
        )
        avg_ctr = await self.db.execute(select(func.avg(Analytics.ctr)))
        avg_retention = await self.db.execute(select(func.avg(Analytics.avg_view_percentage)))

        return {
            "total_views": total_views.scalar() or 0,
            "total_likes": total_likes.scalar() or 0,
            "total_comments": total_comments.scalar() or 0,
            "total_published_videos": total_videos.scalar() or 0,
            "avg_ctr": round(float(avg_ctr.scalar() or 0), 2),
            "avg_retention_pct": round(float(avg_retention.scalar() or 0), 2),
        }

    async def get_top_videos(self, metric: str = "views", limit: int = 10) -> List[Dict]:
        order_col = getattr(Analytics, metric, Analytics.views)
        result = await self.db.execute(
            select(Analytics, Video.title, Video.youtube_url)
            .join(Video, Analytics.video_id == Video.id)
            .order_by(desc(order_col))
            .limit(limit)
        )
        return [
            {
                "video_id": str(row.Analytics.video_id),
                "youtube_video_id": row.Analytics.youtube_video_id,
                "title": row.title,
                "youtube_url": row.youtube_url,
                "views": row.Analytics.views,
                "likes": row.Analytics.likes,
                "comments": row.Analytics.comments,
                "ctr": row.Analytics.ctr,
                "avg_view_percentage": row.Analytics.avg_view_percentage,
            }
            for row in result.all()
        ]

    async def get_best_posting_times(self) -> List[Dict]:
        """Analyze which hours/days get the most views."""
        result = await self.db.execute(
            select(
                func.extract("hour", Video.published_at).label("hour"),
                func.avg(Analytics.views).label("avg_views"),
                func.count(Video.id).label("video_count"),
            )
            .join(Analytics, Analytics.video_id == Video.id)
            .where(Video.published_at.isnot(None))
            .group_by("hour")
            .order_by(desc("avg_views"))
        )
        return [
            {"hour": int(row.hour), "avg_views": float(row.avg_views), "video_count": int(row.video_count)}
            for row in result.all()
        ]

    async def get_content_category_performance(self) -> List[Dict]:
        """Analyze performance by content category."""
        from app.models.content_idea import ContentIdea
        from app.models.script import Script

        result = await self.db.execute(
            select(
                ContentIdea.category,
                func.avg(Analytics.views).label("avg_views"),
                func.avg(Analytics.ctr).label("avg_ctr"),
                func.count(Video.id).label("video_count"),
            )
            .join(Script, Script.content_idea_id == ContentIdea.id)
            .join(Video, Video.script_id == Script.id)
            .join(Analytics, Analytics.video_id == Video.id)
            .group_by(ContentIdea.category)
            .order_by(desc("avg_views"))
        )
        return [
            {
                "category": row.category,
                "avg_views": float(row.avg_views),
                "avg_ctr": float(row.avg_ctr),
                "video_count": int(row.video_count),
            }
            for row in result.all()
        ]
