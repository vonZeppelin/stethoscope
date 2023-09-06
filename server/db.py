from datetime import datetime
from pathlib import Path

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Catalog(Base):
    __tablename__ = "catalog"

    id: Mapped[str] = mapped_column(String(11), primary_key=True)
    parent_id: Mapped[str] = mapped_column(ForeignKey(id), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), index=True)

    title: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    published: Mapped[datetime] = mapped_column(server_default=func.now())
    audio_size: Mapped[int] = mapped_column(nullable=True)
    audio_type: Mapped[str] = mapped_column(String(255), nullable=True)
    duration: Mapped[int] = mapped_column(default=0)
    thumbnail_url: Mapped[str] = mapped_column(String(2083), nullable=True)

    children: Mapped[list["Catalog"]] = relationship(cascade="all, delete-orphan")


async def create_session(location: str) -> async_sessionmaker:
    location = Path(location).resolve()
    location.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{location}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return async_sessionmaker(engine, expire_on_commit=False)
