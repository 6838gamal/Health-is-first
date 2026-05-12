from sqlalchemy import Column, DateTime, String, func
import uuid


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UUIDMixin:
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
