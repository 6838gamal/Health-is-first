from sqlalchemy import Column, String, Float, Boolean, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class Trend(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "trends"

    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_id = Column(String(36), ForeignKey("content_sources.id"), nullable=True)
    trend_score = Column(Float, default=0.0, nullable=False)
    virality_score = Column(Float, default=0.0, nullable=False)
    quality_score = Column(Float, default=0.0, nullable=False)
    category = Column(String(100), nullable=True)
    keywords = Column(JSON, nullable=True)
    is_processed = Column(Boolean, default=False, nullable=False)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    language = Column(String(10), default="ar", nullable=False)
    raw_data = Column(JSON, nullable=True)

    source = relationship("ContentSource", foreign_keys=[source_id])
    content_ideas = relationship("ContentIdea", back_populates="trend")

    __table_args__ = (
        Index("ix_trends_trend_score", "trend_score"),
        Index("ix_trends_is_processed", "is_processed"),
    )

    def __repr__(self):
        return f"<Trend {self.title[:50]}>"
