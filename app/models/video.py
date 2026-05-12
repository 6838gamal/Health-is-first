from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, Enum as SAEnum, Index, JSON
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class VideoStatus(str, enum.Enum):
    pending = "pending"
    generating_audio = "generating_audio"
    generating_subtitles = "generating_subtitles"
    rendering = "rendering"
    review = "review"
    approved = "approved"
    rejected = "rejected"
    scheduled = "scheduled"
    uploading = "uploading"
    published = "published"
    failed = "failed"


class Video(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "videos"

    script_id = Column(String(36), ForeignKey("scripts.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(1000), nullable=True)
    audio_path = Column(String(1000), nullable=True)
    subtitle_path = Column(String(1000), nullable=True)
    thumbnail_id = Column(String(36), ForeignKey("thumbnails.id"), nullable=True)
    duration = Column(Float, nullable=True)
    file_size = Column(Integer, nullable=True)
    resolution = Column(String(20), default="1080x1920", nullable=False)
    status = Column(SAEnum(VideoStatus), default=VideoStatus.pending, nullable=False)
    youtube_video_id = Column(String(100), nullable=True, unique=True)
    youtube_url = Column(String(500), nullable=True)
    youtube_status = Column(String(50), nullable=True)
    scheduled_at = Column(String(50), nullable=True)
    published_at = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    render_metadata = Column(JSON, nullable=True)
    tags = Column(Text, nullable=True)
    category_id = Column(String(10), default="26", nullable=False)
    is_shorts = Column(Boolean, default=True, nullable=False)

    script = relationship("Script", back_populates="videos")
    thumbnail = relationship("Thumbnail", foreign_keys=[thumbnail_id])
    analytics = relationship("Analytics", back_populates="video")
    publishing_queue = relationship("PublishingQueue", back_populates="video")

    __table_args__ = (
        Index("ix_videos_status", "status"),
    )

    def __repr__(self):
        return f"<Video {self.title[:50]}>"
