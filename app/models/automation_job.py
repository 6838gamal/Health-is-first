from sqlalchemy import Column, String, Text, Float, Integer, Enum as SAEnum, DateTime, Index, JSON
import enum
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class JobType(str, enum.Enum):
    collect_trends = "collect_trends"
    generate_ideas = "generate_ideas"
    generate_script = "generate_script"
    generate_audio = "generate_audio"
    render_video = "render_video"
    generate_thumbnail = "generate_thumbnail"
    upload_youtube = "upload_youtube"
    sync_analytics = "sync_analytics"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    retrying = "retrying"
    cancelled = "cancelled"


class AutomationJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "automation_jobs"

    job_type = Column(SAEnum(JobType), nullable=False)
    status = Column(SAEnum(JobStatus), default=JobStatus.pending, nullable=False)
    celery_task_id = Column(String(255), nullable=True, unique=True)
    priority = Column(Integer, default=5, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)
    progress = Column(Float, default=0.0, nullable=False)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    reference_id = Column(String(36), nullable=True)

    __table_args__ = (
        Index("ix_automation_jobs_status", "status"),
        Index("ix_automation_jobs_job_type", "job_type"),
    )

    def __repr__(self):
        return f"<AutomationJob {self.job_type} status={self.status}>"
