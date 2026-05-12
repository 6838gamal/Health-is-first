from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from pydantic import BaseModel
from app.db.base import get_db
from app.models.video import Video, VideoStatus
from app.models.publishing_queue import PublishingQueue, QueueStatus
from app.core.security import get_current_user
from app.tasks.video_tasks import create_video_pipeline
from app.tasks.publisher_tasks import upload_video_youtube
from datetime import datetime, timezone

router = APIRouter(prefix="/videos", tags=["Videos"])


class ApproveVideoRequest(BaseModel):
    scheduled_at: Optional[str] = None
    notes: Optional[str] = None


@router.get("/")
async def list_videos(
    skip: int = 0, limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    query = select(Video).order_by(desc(Video.created_at))
    if status:
        query = query.where(Video.status == status)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    videos = result.scalars().all()
    return {
        "items": [
            {
                "id": str(v.id), "title": v.title,
                "status": v.status.value, "duration": v.duration,
                "file_size": v.file_size, "youtube_url": v.youtube_url,
                "youtube_video_id": v.youtube_video_id,
                "scheduled_at": v.scheduled_at, "published_at": v.published_at,
                "created_at": str(v.created_at),
            }
            for v in videos
        ]
    }


@router.get("/stats")
async def video_stats(db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    stats = {}
    for s in VideoStatus:
        count = await db.execute(select(func.count(Video.id)).where(Video.status == s))
        stats[s.value] = count.scalar()
    return stats


@router.get("/{video_id}")
async def get_video(video_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return {
        "id": str(video.id), "title": video.title, "description": video.description,
        "file_path": video.file_path, "audio_path": video.audio_path,
        "status": video.status.value, "duration": video.duration,
        "resolution": video.resolution, "file_size": video.file_size,
        "youtube_url": video.youtube_url, "youtube_video_id": video.youtube_video_id,
        "youtube_status": video.youtube_status, "scheduled_at": video.scheduled_at,
        "published_at": video.published_at, "error_message": video.error_message,
        "tags": video.tags, "is_shorts": video.is_shorts,
        "created_at": str(video.created_at),
    }


@router.post("/{video_id}/approve")
async def approve_video(
    video_id: str, payload: ApproveVideoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status not in [VideoStatus.review, VideoStatus.rejected]:
        raise HTTPException(status_code=400, detail=f"Video cannot be approved from status: {video.status.value}")

    video.status = VideoStatus.approved
    queue = PublishingQueue(
        video_id=video.id,
        status=QueueStatus.approved,
        priority=5,
        notes=payload.notes,
    )
    if payload.scheduled_at:
        queue.scheduled_at = datetime.fromisoformat(payload.scheduled_at)
        queue.status = QueueStatus.scheduled
        video.status = VideoStatus.scheduled
    session_user_id = current_user.get("user_id")
    db.add(queue)
    await db.flush()

    task = upload_video_youtube.delay(video_id=video_id, queue_id=str(queue.id))
    queue.celery_task_id = task.id
    await db.commit()
    return {"message": "Video approved and queued for upload", "task_id": task.id, "queue_id": str(queue.id)}


@router.post("/{video_id}/reject")
async def reject_video(
    video_id: str,
    notes: str = Body(default="", embed=True),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    video.status = VideoStatus.rejected
    video.error_message = notes
    await db.commit()
    return {"message": "Video rejected"}


@router.post("/{video_id}/regenerate")
async def regenerate_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    script_id = str(video.script_id)
    task = create_video_pipeline.delay(script_id=script_id)
    return {"message": "Video regeneration started", "task_id": task.id}


@router.post("/render/{script_id}")
async def render_video_from_script(script_id: str, _: dict = Depends(get_current_user)):
    task = create_video_pipeline.delay(script_id=script_id)
    return {"task_id": task.id, "status": "queued", "message": "Video rendering started"}
