from datetime import datetime
from pathlib import Path

from sqlalchemy import String, Text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Video(Base):
    __tablename__ = "video"

    id: Mapped[str] = mapped_column(String(11), primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column()
    published: Mapped[datetime] = mapped_column()
    duration: Mapped[int] = mapped_column()
    thumbnail_url: Mapped[str] = mapped_column(String(2083))
    audio_size: Mapped[int] = mapped_column()
    audio_type: Mapped[str] = mapped_column(String(255))


async def create_session(location: str) -> async_sessionmaker:
    location = Path(location).resolve()
    location.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{location}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return async_sessionmaker(engine, expire_on_commit=False)
