from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from app.db.base import get_db
from app.models.analytics import Analytics
from app.models.video import Video, VideoStatus
from app.core.security import get_current_user
from app.tasks.analytics_tasks import sync_all_analytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    total_views = await db.execute(select(func.sum(Analytics.views)))
    total_likes = await db.execute(select(func.sum(Analytics.likes)))
    total_comments = await db.execute(select(func.sum(Analytics.comments)))
    total_videos = await db.execute(select(func.count(Video.id)).where(Video.status == VideoStatus.published))
    avg_ctr = await db.execute(select(func.avg(Analytics.ctr)))
    avg_retention = await db.execute(select(func.avg(Analytics.avg_view_percentage)))

    return {
        "total_views": total_views.scalar() or 0,
        "total_likes": total_likes.scalar() or 0,
        "total_comments": total_comments.scalar() or 0,
        "total_published_videos": total_videos.scalar() or 0,
        "avg_ctr": round(float(avg_ctr.scalar() or 0), 2),
        "avg_retention": round(float(avg_retention.scalar() or 0), 2),
    }


@router.get("/top-videos")
async def get_top_videos(
    limit: int = 10,
    metric: str = Query(default="views", enum=["views", "likes", "comments", "ctr"]),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    order_col = getattr(Analytics, metric, Analytics.views)
    result = await db.execute(
        select(Analytics, Video.title, Video.youtube_url)
        .join(Video, Analytics.video_id == Video.id)
        .order_by(desc(order_col))
        .limit(limit)
    )
    rows = result.all()
    return {
        "items": [
            {
                "youtube_video_id": a.Analytics.youtube_video_id,
                "title": a.title,
                "youtube_url": a.youtube_url,
                "views": a.Analytics.views,
                "likes": a.Analytics.likes,
                "comments": a.Analytics.comments,
                "ctr": a.Analytics.ctr,
                "avg_view_percentage": a.Analytics.avg_view_percentage,
                "fetch_date": str(a.Analytics.fetch_date),
            }
            for a in rows
        ]
    }


@router.get("/video/{video_id}")
async def get_video_analytics(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Analytics).where(Analytics.video_id == video_id).order_by(desc(Analytics.fetch_date))
    )
    analytics = result.scalars().all()
    return {
        "video_id": video_id,
        "history": [
            {
                "fetch_date": str(a.fetch_date),
                "views": a.views, "likes": a.likes, "comments": a.comments,
                "ctr": a.ctr, "avg_view_percentage": a.avg_view_percentage,
            }
            for a in analytics
        ]
    }


@router.post("/sync")
async def trigger_sync(_: dict = Depends(get_current_user)):
    task = sync_all_analytics.delay()
    return {"task_id": task.id, "status": "queued", "message": "Analytics sync started"}
