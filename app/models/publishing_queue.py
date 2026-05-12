from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum as SAEnum, DateTime, Index, JSON
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class QueueStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    scheduled = "scheduled"
    uploading = "uploading"
    published = "published"
    failed = "failed"
    cancelled = "cancelled"


class PublishingQueue(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "publishing_queue"

    video_id = Column(String(36), ForeignKey("videos.id"), nullable=False)
    status = Column(SAEnum(QueueStatus), default=QueueStatus.pending, nullable=False)
    priority = Column(Integer, default=5, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)
    celery_task_id = Column(String(255), nullable=True)
    youtube_response = Column(JSON, nullable=True)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    video = relationship("Video", back_populates="publishing_queue")
    approver = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        Index("ix_publishing_queue_status", "status"),
    )

    def __repr__(self):
        return f"<PublishingQueue {self.id} status={self.status}>"
