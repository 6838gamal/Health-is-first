import logging
import os
from typing import Optional, Dict
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from app.core.config import settings

logger = logging.getLogger(__name__)

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtubepartner",
]


class YouTubeService:
    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service

        credentials = Credentials(
            token=None,
            refresh_token=settings.YOUTUBE_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.YOUTUBE_CLIENT_ID,
            client_secret=settings.YOUTUBE_CLIENT_SECRET,
            scopes=YOUTUBE_SCOPES,
        )
        credentials.refresh(Request())
        self._service = build("youtube", "v3", credentials=credentials)
        return self._service

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list,
        thumbnail_path: Optional[str] = None,
        scheduled_at: Optional[str] = None,
        category_id: str = "26",
        is_shorts: bool = True,
    ) -> Dict:
        service = self._get_service()

        # Ensure Shorts hashtag
        if is_shorts and "#shorts" not in description.lower():
            description = f"{description}\n\n#Shorts #shorts"

        status = {
            "privacyStatus": "private" if scheduled_at else "public",
            "selfDeclaredMadeForKids": False,
        }
        if scheduled_at:
            status["publishAt"] = scheduled_at

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:500],
                "categoryId": category_id,
                "defaultLanguage": "ar",
                "defaultAudioLanguage": "ar",
            },
            "status": status,
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5,  # 5MB chunks
        )

        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status_code, response = request.next_chunk()
            if status_code:
                logger.info(f"Upload progress: {int(status_code.progress() * 100)}%")

        video_id = response.get("id")
        logger.info(f"Video uploaded: {video_id}")

        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                self.set_thumbnail(video_id, thumbnail_path)
            except Exception as e:
                logger.warning(f"Thumbnail upload failed: {e}")

        return {
            "video_id": video_id,
            "url": f"https://www.youtube.com/shorts/{video_id}",
            "status": response.get("status", {}),
        }

    def set_thumbnail(self, video_id: str, thumbnail_path: str):
        service = self._get_service()
        media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
        service.thumbnails().set(videoId=video_id, media_body=media).execute()
        logger.info(f"Thumbnail set for video: {video_id}")

    def get_video_stats(self, video_id: str) -> Dict:
        service = self._get_service()
        response = service.videos().list(
            part="statistics,snippet,status",
            id=video_id,
        ).execute()
        items = response.get("items", [])
        if items:
            item = items[0]
            stats = item.get("statistics", {})
            return {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "status": item.get("status", {}).get("uploadStatus"),
            }
        return {}

    def get_channel_analytics(self) -> Dict:
        service = self._get_service()
        response = service.channels().list(
            part="statistics",
            id=settings.YOUTUBE_CHANNEL_ID,
        ).execute()
        items = response.get("items", [])
        if items:
            return items[0].get("statistics", {})
        return {}
