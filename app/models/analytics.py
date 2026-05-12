from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Index, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class Analytics(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "analytics"

    video_id = Column(String(36), ForeignKey("videos.id"), nullable=False)
    youtube_video_id = Column(String(100), nullable=True, index=True)
    fetch_date = Column(DateTime(timezone=True), nullable=True)
    views = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    dislikes = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)
    impressions = Column(Integer, default=0, nullable=False)
    ctr = Column(Float, default=0.0, nullable=False)
    avg_view_duration = Column(Float, default=0.0, nullable=False)
    avg_view_percentage = Column(Float, default=0.0, nullable=False)
    subscribers_gained = Column(Integer, default=0, nullable=False)
    revenue = Column(Float, default=0.0, nullable=False)
    raw_data = Column(JSON, nullable=True)

    video = relationship("Video", back_populates="analytics")

    __table_args__ = (
        Index("ix_analytics_video_id", "video_id"),
    )

    def __repr__(self):
        return f"<Analytics video={self.youtube_video_id} views={self.views}>"
