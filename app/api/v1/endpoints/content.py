from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from pydantic import BaseModel
from app.db.base import get_db
from app.models.content_idea import ContentIdea, IdeaStatus
from app.models.script import Script, ScriptStatus
from app.core.security import get_current_user
from app.tasks.content_tasks import generate_content_ideas_batch, generate_script

router = APIRouter(prefix="/content", tags=["Content"])


class ScriptUpdateRequest(BaseModel):
    title: Optional[str] = None
    hook: Optional[str] = None
    body: Optional[str] = None
    cta: Optional[str] = None
    full_script: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None
    status: Optional[str] = None
    reviewer_notes: Optional[str] = None


@router.get("/ideas")
async def list_ideas(
    skip: int = 0, limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    query = select(ContentIdea).order_by(desc(ContentIdea.estimated_virality))
    if status:
        query = query.where(ContentIdea.status == status)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    ideas = result.scalars().all()
    return {
        "items": [
            {
                "id": str(i.id), "title": i.title, "hook": i.hook,
                "angle": i.angle, "category": i.category,
                "estimated_virality": i.estimated_virality,
                "status": i.status.value, "safety_check_passed": i.safety_check_passed,
                "created_at": str(i.created_at),
            }
            for i in ideas
        ]
    }


@router.post("/ideas/generate")
async def trigger_idea_generation(
    limit: int = Body(default=10, embed=True),
    _: dict = Depends(get_current_user),
):
    task = generate_content_ideas_batch.delay(limit=limit)
    return {"task_id": task.id, "status": "queued"}


@router.post("/ideas/{idea_id}/generate-script")
async def trigger_script_generation(idea_id: str, _: dict = Depends(get_current_user)):
    task = generate_script.delay(idea_id=idea_id)
    return {"task_id": task.id, "status": "queued"}


@router.get("/scripts")
async def list_scripts(
    skip: int = 0, limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    query = select(Script).order_by(desc(Script.created_at))
    if status:
        query = query.where(Script.status == status)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    scripts = result.scalars().all()
    return {
        "items": [
            {
                "id": str(s.id), "title": s.title, "hook": s.hook,
                "estimated_duration": s.estimated_duration,
                "status": s.status.value, "safety_approved": s.safety_approved,
                "language": s.language, "created_at": str(s.created_at),
            }
            for s in scripts
        ]
    }


@router.get("/scripts/{script_id}")
async def get_script(script_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return {
        "id": str(script.id), "title": script.title, "hook": script.hook,
        "body": script.body, "cta": script.cta, "full_script": script.full_script,
        "description": script.description, "hashtags": script.hashtags,
        "estimated_duration": script.estimated_duration, "word_count": script.word_count,
        "status": script.status.value, "safety_approved": script.safety_approved,
        "reviewer_notes": script.reviewer_notes, "created_at": str(script.created_at),
    }


@router.put("/scripts/{script_id}")
async def update_script(
    script_id: str, payload: ScriptUpdateRequest,
    db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user),
):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    for field, value in payload.dict(exclude_none=True).items():
        if field == "status":
            script.status = ScriptStatus(value)
        else:
            setattr(script, field, value)
    await db.commit()
    return {"message": "Script updated", "id": script_id}
