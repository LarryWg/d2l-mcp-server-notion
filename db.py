"""
db.py
Async SQLAlchemy engine, session factory, and all ORM models.

Models live here (rather than a separate models/ folder) to keep the MVP
lean. They can be split out later as the schema grows.
"""

from __future__ import annotations

from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import get_settings

settings = get_settings()

# Engine 

engine = create_async_engine(
    settings.postgres_url,
    echo=(settings.app_env == "development"),  # SQL logging in dev only
    pool_pre_ping=True,                         # reconnect on stale connections
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Base 

class Base(DeclarativeBase):
    pass


# Models 

class Course(Base):
    """A D2L course (org unit)."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    d2l_org_unit_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Course id={self.d2l_org_unit_id} name={self.name!r}>"


class Assignment(Base):
    """A D2L dropbox / assignment folder."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    d2l_assignment_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)

    name: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_points: Mapped[float | None] = mapped_column(nullable=True)

    notion_page_id: Mapped[str] = mapped_column(String(100), default="")
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    course: Mapped["Course"] = relationship(back_populates="assignments")

    def __repr__(self) -> str:
        return f"<Assignment id={self.d2l_assignment_id} name={self.name!r}>"


class Quiz(Base):
    """A D2L quiz."""

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    d2l_quiz_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)

    name: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts_allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notion_page_id: Mapped[str] = mapped_column(String(100), default="")
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    course: Mapped["Course"] = relationship(back_populates="quizzes")

    def __repr__(self) -> str:
        return f"<Quiz id={self.d2l_quiz_id} name={self.name!r}>"


# Helpers 

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables. Called once at application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)