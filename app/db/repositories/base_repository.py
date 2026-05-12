from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: str) -> Optional[ModelType]:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, **kwargs) -> ModelType:
        obj = self.model(**kwargs)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, id: str, **kwargs) -> Optional[ModelType]:
        obj = await self.get(id)
        if not obj:
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def delete(self, id: str) -> bool:
        obj = await self.get(id)
        if not obj:
            return False
        await self.db.delete(obj)
        return True
