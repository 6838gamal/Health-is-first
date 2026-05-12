from sqlalchemy import Column, String, Text, Float, Integer, Boolean, ForeignKey, Enum as SAEnum, Index, JSON
import enum
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class AIOperation(str, enum.Enum):
    trend_analysis = "trend_analysis"
    idea_generation = "idea_generation"
    script_generation = "script_generation"
    safety_check = "safety_check"
    thumbnail_prompt = "thumbnail_prompt"
    content_analysis = "content_analysis"


class AILog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ai_logs"

    operation = Column(SAEnum(AIOperation), nullable=False)
    model_used = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Float, nullable=True)
    cost_usd = Column(Float, default=0.0, nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    reference_id = Column(String(36), nullable=True)

    __table_args__ = (
        Index("ix_ai_logs_operation", "operation"),
    )

    def __repr__(self):
        return f"<AILog {self.operation} success={self.success}>"
