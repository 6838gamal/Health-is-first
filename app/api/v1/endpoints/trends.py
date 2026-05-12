from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from app.db.base import get_db
from app.models.trend import Trend
from app.core.security import get_current_user
from app.tasks.collection_tasks import collect_rss_feeds, collect_all_trends

router = APIRouter(prefix="/trends", tags=["Trends"])


@router.get("/")
async def list_trends(
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    is_processed: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    query = select(Trend).order_by(desc(Trend.trend_score))
    if category:
        query = query.where(Trend.category == category)
    if is_processed is not None:
        query = query.where(Trend.is_processed == is_processed)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    trends = result.scalars().all()
    return {
        "items": [
            {
                "id": str(t.id),
                "title": t.title,
                "summary": t.summary,
                "source_url": t.source_url,
                "trend_score": t.trend_score,
                "quality_score": t.quality_score,
                "category": t.category,
                "is_processed": t.is_processed,
                "created_at": str(t.created_at),
            }
            for t in trends
        ],
        "skip": skip,
        "limit": limit,
    }


@router.get("/stats")
async def trend_stats(db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    total = await db.execute(select(func.count(Trend.id)))
    processed = await db.execute(select(func.count(Trend.id)).where(Trend.is_processed == True))
    pending = await db.execute(select(func.count(Trend.id)).where(Trend.is_processed == False))
    return {
        "total": total.scalar(),
        "processed": processed.scalar(),
        "pending": pending.scalar(),
    }


@router.post("/collect/rss")
async def trigger_rss_collection(_: dict = Depends(get_current_user)):
    task = collect_rss_feeds.delay()
    return {"task_id": task.id, "status": "queued", "message": "RSS collection started"}


@router.post("/collect/trends")
async def trigger_trend_collection(_: dict = Depends(get_current_user)):
    task = collect_all_trends.delay()
    return {"task_id": task.id, "status": "queued", "message": "Trend collection started"}


@router.get("/{trend_id}")
async def get_trend(trend_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    result = await db.execute(select(Trend).where(Trend.id == trend_id))
    trend = result.scalar_one_or_none()
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    return {"id": str(trend.id), "title": trend.title, "summary": trend.summary,
            "source_url": trend.source_url, "trend_score": trend.trend_score,
            "quality_score": trend.quality_score, "category": trend.category,
            "keywords": trend.keywords, "raw_data": trend.raw_data,
            "is_processed": trend.is_processed, "created_at": str(trend.created_at)}
