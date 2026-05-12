from sqlalchemy import Column, String, Boolean, Integer, Float, Enum as SAEnum, Text, JSON
import enum
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class SourceType(str, enum.Enum):
    rss = "rss"
    reddit = "reddit"
    google_trends = "google_trends"
    pubmed = "pubmed"
    website = "website"


class ContentSource(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "content_sources"

    name = Column(String(255), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    source_type = Column(SAEnum(SourceType), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    reliability_score = Column(Float, default=5.0, nullable=False)
    fetch_interval = Column(Integer, default=3600, nullable=False)
    last_fetched_at = Column(String(50), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    language = Column(String(10), default="ar", nullable=False)

    def __repr__(self):
        return f"<ContentSource {self.name}>"
