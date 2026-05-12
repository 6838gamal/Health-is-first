from sqlalchemy import Column, String, Float, Boolean, Text, ForeignKey, Enum as SAEnum, Index, JSON
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class IdeaStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    in_production = "in_production"
    completed = "completed"


class ContentIdea(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "content_ideas"

    title = Column(String(500), nullable=False)
    hook = Column(Text, nullable=True)
    angle = Column(Text, nullable=True)
    target_keywords = Column(JSON, nullable=True)
    category = Column(String(100), nullable=True)
    estimated_virality = Column(Float, default=0.0, nullable=False)
    status = Column(SAEnum(IdeaStatus), default=IdeaStatus.pending, nullable=False)
    trend_id = Column(String(36), ForeignKey("trends.id"), nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    safety_check_passed = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    trend = relationship("Trend", back_populates="content_ideas")
    scripts = relationship("Script", back_populates="content_idea")

    __table_args__ = (
        Index("ix_content_ideas_status", "status"),
        Index("ix_content_ideas_virality", "estimated_virality"),
    )

    def __repr__(self):
        return f"<ContentIdea {self.title[:50]}>"
