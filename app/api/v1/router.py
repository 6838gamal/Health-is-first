from fastapi import APIRouter
from app.api.v1.endpoints import auth, trends, content, videos, analytics, jobs

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(trends.router)
api_router.include_router(content.router)
api_router.include_router(videos.router)
api_router.include_router(analytics.router)
api_router.include_router(jobs.router)
