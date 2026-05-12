from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
from app.db.base import get_db
from app.models.automation_job import AutomationJob, JobStatus
from app.core.security import get_current_user
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/jobs", tags=["Automation Jobs"])


@router.get("/")
async def list_jobs(
    skip: int = 0, limit: int = 50,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    query = select(AutomationJob).order_by(desc(AutomationJob.created_at))
    if status:
        query = query.where(AutomationJob.status == status)
    if job_type:
        query = query.where(AutomationJob.job_type == job_type)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()
    return {
        "items": [
            {
                "id": str(j.id), "job_type": j.job_type.value,
                "status": j.status.value, "progress": j.progress,
                "celery_task_id": j.celery_task_id,
                "started_at": str(j.started_at) if j.started_at else None,
                "completed_at": str(j.completed_at) if j.completed_at else None,
                "error_message": j.error_message,
                "retry_count": j.retry_count,
                "created_at": str(j.created_at),
            }
            for j in jobs
        ]
    }


@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str, _: dict = Depends(get_current_user)):
    task = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None,
        "traceback": task.traceback if task.failed() else None,
    }


@router.post("/run/full-pipeline")
async def run_full_pipeline(_: dict = Depends(get_current_user)):
    from app.tasks.collection_tasks import collect_rss_feeds, collect_all_trends
    from app.tasks.content_tasks import generate_content_ideas_batch

    t1 = collect_rss_feeds.delay()
    t2 = collect_all_trends.delay()
    t3 = generate_content_ideas_batch.delay(limit=5)

    return {
        "message": "Full pipeline started",
        "tasks": {
            "collect_rss": t1.id,
            "collect_trends": t2.id,
            "generate_ideas": t3.id,
        }
    }
