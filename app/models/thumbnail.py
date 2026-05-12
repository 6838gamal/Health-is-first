from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class ThumbnailStatus(str, enum.Enum):
    pending = "pending"
    generated = "generated"
    approved = "approved"
    rejected = "rejected"


class Thumbnail(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "thumbnails"

    script_id = Column(String(36), ForeignKey("scripts.id"), nullable=True)
    file_path = Column(String(1000), nullable=True)
    title_text = Column(String(500), nullable=True)
    subtitle_text = Column(String(500), nullable=True)
    background_color = Column(String(20), default="#1a1a2e", nullable=False)
    accent_color = Column(String(20), default="#e94560", nullable=False)
    text_color = Column(String(20), default="#ffffff", nullable=False)
    ai_prompt = Column(Text, nullable=True)
    generation_metadata = Column(JSON, nullable=True)
    status = Column(SAEnum(ThumbnailStatus), default=ThumbnailStatus.pending, nullable=False)
    is_uploaded = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Thumbnail {self.id}>"
