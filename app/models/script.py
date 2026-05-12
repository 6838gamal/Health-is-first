from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class ScriptStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    rejected = "rejected"
    in_production = "in_production"


class Script(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scripts"

    content_idea_id = Column(String(36), ForeignKey("content_ideas.id"), nullable=False)
    title = Column(String(500), nullable=False)
    hook = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    cta = Column(Text, nullable=False)
    full_script = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)
    estimated_duration = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    language = Column(String(10), default="ar", nullable=False)
    status = Column(SAEnum(ScriptStatus), default=ScriptStatus.draft, nullable=False)
    safety_approved = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    ai_model_used = Column(String(100), nullable=True)
    generation_metadata = Column(JSON, nullable=True)
    reviewer_notes = Column(Text, nullable=True)

    content_idea = relationship("ContentIdea", back_populates="scripts")
    videos = relationship("Video", back_populates="script")

    def __repr__(self):
        return f"<Script {self.title[:50]}>"
