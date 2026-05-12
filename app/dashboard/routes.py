from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from datetime import datetime, date

from app.db.base import get_db, AsyncSessionLocal
from app.models.trend import Trend
from app.models.content_idea import ContentIdea, IdeaStatus
from app.models.script import Script, ScriptStatus
from app.models.video import Video, VideoStatus
from app.models.thumbnail import Thumbnail
from app.models.automation_job import AutomationJob
from app.models.analytics import Analytics
from app.core.security import verify_password, create_access_token, decode_token
from app.models.user import User

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
templates = Jinja2Templates(directory="app/templates")


def get_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get("access_token")


async def get_current_user_from_cookie(request: Request) -> Optional[dict]:
    token = get_token_from_cookie(request)
    if not token:
        return None
    try:
        return decode_token(token)
    except Exception:
        return None


async def get_dashboard_stats(db: AsyncSession) -> dict:
    trends_pending = await db.execute(select(func.count(Trend.id)).where(Trend.is_processed == False))
    scripts_ready = await db.execute(select(func.count(Script.id)).where(Script.status == ScriptStatus.review))
    videos_review = await db.execute(select(func.count(Video.id)).where(Video.status == VideoStatus.review))
    videos_published = await db.execute(select(func.count(Video.id)).where(Video.status == VideoStatus.published))
    ideas_generated = await db.execute(select(func.count(ContentIdea.id)))
    total_views = await db.execute(select(func.sum(Analytics.views)))
    total_likes = await db.execute(select(func.sum(Analytics.likes)))
    jobs_running = await db.execute(select(func.count(AutomationJob.id)).where(AutomationJob.status == "running"))
    return {
        "trends_pending": trends_pending.scalar() or 0,
        "scripts_ready": scripts_ready.scalar() or 0,
        "videos_review": videos_review.scalar() or 0,
        "videos_published": videos_published.scalar() or 0,
        "ideas_generated": ideas_generated.scalar() or 0,
        "total_views": total_views.scalar() or 0,
        "total_likes": total_likes.scalar() or 0,
        "jobs_running": jobs_running.scalar() or 0,
    }


# ── Auth ─────────────────────────────────────────────────────────────────────

@dashboard_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "dashboard/login.html", {})


@dashboard_router.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            return templates.TemplateResponse(
                request, "dashboard/login.html", {"error": "بيانات الدخول غير صحيحة"}
            )
        token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie("access_token", token, httponly=True, max_age=86400)
        return response


@dashboard_router.get("/logout")
async def logout():
    response = RedirectResponse(url="/dashboard/login", status_code=302)
    response.delete_cookie("access_token")
    return response


# ── Main Dashboard ────────────────────────────────────────────────────────────

@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/dashboard/login", status_code=302)

    stats = await get_dashboard_stats(db)
    result = await db.execute(select(Video).order_by(desc(Video.created_at)).limit(8))
    recent_videos = result.scalars().all()

    return templates.TemplateResponse(request, "dashboard/index.html", {
        "active_page": "dashboard",
        "stats": stats,
        "recent_videos": recent_videos,
        "current_date": date.today().strftime("%Y-%m-%d"),
        "pending_review_count": stats["videos_review"],
    })


# ── Trends ───────────────────────────────────────────────────────────────────

@dashboard_router.get("/trends", response_class=HTMLResponse)
async def trends_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/dashboard/login", status_code=302)

    result = await db.execute(
        select(Trend).order_by(desc(Trend.trend_score)).limit(100)
    )
    trends_raw = result.scalars().all()
    trends = [
        {
            "id": str(t.id), "title": t.title, "summary": t.summary,
            "category": t.category, "trend_score": t.trend_score,
            "quality_score": t.quality_score, "is_processed": t.is_processed,
            "created_at": str(t.created_at),
        }
        for t in trends_raw
    ]
    stats = await get_dashboard_stats(db)
    return templates.TemplateResponse(request, "dashboard/trends.html", {
        "active_page": "trends",
        "trends": trends,
        "pending_review_count": stats["videos_review"],
    })


# ── Ideas ────────────────────────────────────────────────────────────────────

@dashboard_router.get("/ideas", response_class=HTMLResponse)
async def ideas_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/dashboard/login", status_code=302)

    result = await db.execute(
        select(ContentIdea).order_by(desc(ContentIdea.estimated_virality)).limit(50)
    )
    ideas_raw = result.scalars().all()
    ideas = [
        {
            "id": str(i.id), "title": i.title, "hook": i.hook,
            "category": i.category, "estimated_virality": i.estimated_virality,
            "status": i.status.value, "safety_check_passed": i.safety_check_passed,
        }
        for i in ideas_raw
    ]
    stats = await get_dashboard_stats(db)
    return templates.TemplateResponse(request, "dashboard/ideas.html", {
        "active_page": "ideas",
        "ideas": ideas,
        "pending_review_count": stats["videos_review"],
    })


# ── Scripts ──────────────────────────────────────────────────────────────────

@dashboard_router.get("/scripts", response_class=HTMLResponse)
async def scripts_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/dashboard/login", status_code=302)

    result = await db.execute(select(Script).order_by(desc(Script.created_at)).limit(50))
    scripts_raw = result.scalars().all()
    scripts = [
        {
            "id": str(s.id), "title": s.title, "status": s.status.value,
            "estimated_duration": s.estimated_duration, "language": s.language,
            "safety_approved": s.safety_approved, "created_at": str(s.created_at),
        }
        for s in scripts_raw
    ]
    stats = await get_dashboard_stats(db)
    return templates.TemplateResponse(request, "dashboard/scripts.html", {
        "active_page": "scripts",
        "scripts": scripts,
        "pending_review_count": stats["videos_review"],
    })


# ── Videos ──────────────────────────────────────────────────────────────────

@dashboard_router.get("/videos", response_class=HTMLResponse)
async def videos_page(
    request: Request, status: str = "", db: AsyncSession = Depends(get_db)
):
    user = await get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/dashboard/login", status_code=302)

    query = select(Video).order_by(desc(Video.created_at))
    if status:
        try:
            query = query.where(Video.status == VideoStatus(status))
        except ValueError:
            pass
    result = await db.execute(query.limit(50))
    videos_raw = result.scalars().all()
    videos = [
        {
            "id": str(v.id), "title": v.title, "status": v.status.value,
            "duration": v.duration, "file_size": v.file_size,
            "youtube_url": v.youtube_url, "created_at": v.created_at,
        }
        for v in videos_raw
    ]

    counts = {}
    for s in VideoStatus:
        c = await db.execute(select(func.count(Video.id)).where(Video.status == s))
        counts[s.value] = c.scalar() or 0

    stats = await get_dashboard_stats(db)
    return templates.TemplateResponse(request, "dashboard/videos.html", {
        "active_page": "videos",
        "videos": videos, "counts": counts, "current_status": status,
        "pending_review_count": stats["videos_review"],
    })


# ── Review ──────────────────────────────────────────────────────────────────

@dashboard_router.get("/review", response_class=HTMLResponse)
async def review_page(
    request: Request, status: str = "review", page: int = 1, db: AsyncSession = Depends(get_db)
):
    user = await get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/dashboard/login", status_code=302)

    per_page = 12
    query = select(Video).order_by(desc(Video.created_at))
    if status != "all":
        try:
            query = query.where(Video.status == VideoStatus(status))
        except ValueError:
            pass

    result = await db.execute(query.offset((page - 1) * per_page).limit(per_page))
    videos_raw = result.scalars().all()

    videos = []
    for v in videos_raw:
        vd = {
            "id": str(v.id), "title": v.title, "description": v.description,
            "status": v.status.value, "duration": v.duration,
            "youtube_url": v.youtube_url, "file_path": v.file_path,
            "thumbnail_path": None, "created_at": v.created_at,
        }
        if v.thumbnail_id:
            tr = await db.execute(select(Thumbnail).where(Thumbnail.id == v.thumbnail_id))
            thumb = tr.scalar_one_or_none()
            if thumb:
                vd["thumbnail_path"] = thumb.file_path
        videos.append(vd)

    counts = {}
    for s in VideoStatus:
        c = await db.execute(select(func.count(Video.id)).where(Video.status == s))
        counts[s.value] = c.scalar() or 0

    stats = await get_dashboard_stats(db)
    total = counts.get(status, sum(counts.values()) if status == "all" else 0)
    return templates.TemplateResponse(request, "dashboard/review.html", {
        "active_page": "review",
        "videos": videos, "current_status": status, "counts": counts,
        "current_page": page, "total_pages": max(1, total // per_page + 1),
        "pending_review_count": stats["videos_review"],
    })


@dashboard_router.get("/review/{video_id}", response_class=HTMLResponse)
async def review_detail(video_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/dashboard/login", status_code=302)

    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    script = None
    if video.script_id:
        sr = await db.execute(select(Script).where(Script.id == video.script_id))
        script = sr.scalar_one_or_none()

    thumbnail_path = None
    if video.thumbnail_id:
        tr = await db.execute(select(Thumbnail).where(Thumbnail.id == video.thumbnail_id))
        thumb = tr.scalar_one_or_none()
        if thumb:
            thumbnail_path = thumb.file_path

    stats = await get_dashboard_stats(db)
    return templates.TemplateResponse(request, "dashboard/review_detail.html", {
        "active_page": "review",
        "video": video, "script": script, "thumbnail_path": thumbnail_path,
        "pending_review_count": stats["videos_review"],
    })


# ── Analytics ────────────────────────────────────────────────────────────────

@dashboard_router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/dashboard/login", status_code=302)

    total_views = await db.execute(select(func.sum(Analytics.views)))
    total_likes = await db.execute(select(func.sum(Analytics.likes)))
    total_comments = await db.execute(select(func.sum(Analytics.comments)))
    total_pub = await db.execute(select(func.count(Video.id)).where(Video.status == VideoStatus.published))
    avg_ctr = await db.execute(select(func.avg(Analytics.ctr)))
    avg_ret = await db.execute(select(func.avg(Analytics.avg_view_percentage)))

    overview = {
        "total_views": total_views.scalar() or 0,
        "total_likes": total_likes.scalar() or 0,
        "total_comments": total_comments.scalar() or 0,
        "total_published_videos": total_pub.scalar() or 0,
        "avg_ctr": round(float(avg_ctr.scalar() or 0), 2),
        "avg_retention": round(float(avg_ret.scalar() or 0), 2),
    }

    top_result = await db.execute(
        select(Analytics, Video.title, Video.youtube_url)
        .join(Video, Analytics.video_id == Video.id)
        .order_by(desc(Analytics.views)).limit(10)
    )
    top_videos = [
        {
            "title": row.title, "youtube_url": row.youtube_url,
            "youtube_video_id": row.Analytics.youtube_video_id,
            "views": row.Analytics.views, "likes": row.Analytics.likes,
            "comments": row.Analytics.comments, "ctr": row.Analytics.ctr,
            "avg_view_percentage": row.Analytics.avg_view_percentage,
        }
        for row in top_result.all()
    ]

    stats = await get_dashboard_stats(db)
    return templates.TemplateResponse(request, "dashboard/analytics.html", {
        "active_page": "analytics",
        "overview": overview, "top_videos": top_videos,
        "pending_review_count": stats["videos_review"],
    })


# ── Jobs ─────────────────────────────────────────────────────────────────────

@dashboard_router.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/dashboard/login", status_code=302)

    result = await db.execute(select(AutomationJob).order_by(desc(AutomationJob.created_at)).limit(50))
    jobs = [
        {
            "id": str(j.id), "job_type": j.job_type.value, "status": j.status.value,
            "progress": j.progress, "celery_task_id": j.celery_task_id,
            "started_at": str(j.started_at) if j.started_at else None,
            "completed_at": str(j.completed_at) if j.completed_at else None,
            "error_message": j.error_message, "retry_count": j.retry_count,
            "created_at": str(j.created_at),
        }
        for j in result.scalars().all()
    ]
    stats = await get_dashboard_stats(db)
    return templates.TemplateResponse(request, "dashboard/jobs.html", {
        "active_page": "jobs",
        "jobs": jobs,
        "pending_review_count": stats["videos_review"],
    })


# ── HTMX Action APIs ─────────────────────────────────────────────────────────

@dashboard_router.post("/api/run-pipeline")
async def api_run_pipeline():
    try:
        from app.tasks.collection_tasks import collect_rss_feeds, collect_all_trends
        from app.tasks.content_tasks import generate_content_ideas_batch
        collect_rss_feeds.delay()
        collect_all_trends.delay()
        generate_content_ideas_batch.delay(limit=5)
        return JSONResponse({"status": "ok"}, headers={"X-Toast-Message": "تم تشغيل خط الإنتاج"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=200)


@dashboard_router.post("/api/collect-trends")
async def api_collect_trends():
    try:
        from app.tasks.collection_tasks import collect_all_trends
        collect_all_trends.delay()
    except Exception:
        pass
    return JSONResponse({"status": "ok"})


@dashboard_router.post("/api/collect-rss")
async def api_collect_rss():
    try:
        from app.tasks.collection_tasks import collect_rss_feeds
        collect_rss_feeds.delay()
    except Exception:
        pass
    return JSONResponse({"status": "ok"})


@dashboard_router.post("/api/generate-ideas")
async def api_generate_ideas():
    try:
        from app.tasks.content_tasks import generate_content_ideas_batch
        generate_content_ideas_batch.delay(limit=10)
    except Exception:
        pass
    return JSONResponse({"status": "ok"})


@dashboard_router.post("/api/sync-analytics")
async def api_sync_analytics():
    try:
        from app.tasks.analytics_tasks import sync_all_analytics
        sync_all_analytics.delay()
    except Exception:
        pass
    return JSONResponse({"status": "ok"})


@dashboard_router.post("/api/ideas/{idea_id}/generate-script")
async def api_generate_script(idea_id: str):
    try:
        from app.tasks.content_tasks import generate_script
        generate_script.delay(idea_id=idea_id)
    except Exception:
        pass
    return JSONResponse({"status": "ok"})


@dashboard_router.post("/api/videos/{video_id}/approve")
async def api_approve_video(video_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.publishing_queue import PublishingQueue, QueueStatus
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return JSONResponse({"error": "Not found"}, status_code=404)
    video.status = VideoStatus.approved
    queue = PublishingQueue(video_id=video.id, status=QueueStatus.approved, priority=5)
    db.add(queue)
    await db.flush()
    try:
        from app.tasks.publisher_tasks import upload_video_youtube
        task = upload_video_youtube.delay(video_id=video_id, queue_id=str(queue.id))
        queue.celery_task_id = task.id
    except Exception:
        pass
    await db.commit()
    return JSONResponse({"status": "ok"})


@dashboard_router.post("/api/videos/{video_id}/update-meta")
async def api_update_video_meta(video_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if title:
        video.title = title
    if description is not None:
        video.description = description
    await db.commit()
    return JSONResponse({"status": "ok"}, headers={"X-Toast-Message": "تم حفظ التعديلات بنجاح"})


@dashboard_router.post("/api/videos/{video_id}/reject")
async def api_reject_video(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if video:
        video.status = VideoStatus.rejected
        await db.commit()
    return JSONResponse({"status": "ok"})


@dashboard_router.post("/api/videos/{video_id}/regenerate")
async def api_regenerate_video(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return JSONResponse({"error": "Not found"}, status_code=404)
    try:
        from app.tasks.video_tasks import create_video_pipeline
        task = create_video_pipeline.delay(script_id=str(video.script_id))
        return JSONResponse({"status": "ok", "task_id": task.id})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@dashboard_router.post("/api/videos/{video_id}/schedule")
async def api_schedule_video(video_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    from app.models.publishing_queue import PublishingQueue, QueueStatus
    form = await request.form()
    scheduled_at_str = form.get("scheduled_at")

    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return JSONResponse({"error": "Not found"}, status_code=404)

    video.status = VideoStatus.scheduled
    queue = PublishingQueue(video_id=video.id, status=QueueStatus.scheduled, priority=5)
    if scheduled_at_str:
        queue.scheduled_at = datetime.fromisoformat(scheduled_at_str)
    db.add(queue)
    await db.flush()
    try:
        from app.tasks.publisher_tasks import upload_video_youtube
        task = upload_video_youtube.delay(video_id=video_id, queue_id=str(queue.id))
        queue.celery_task_id = task.id
    except Exception:
        pass
    await db.commit()
    return JSONResponse({"status": "ok"})
