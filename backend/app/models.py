from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)

    user_id: Mapped[str] = mapped_column(String(128), index=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)

    platform: Mapped[str] = mapped_column(String(16), index=True)
    app_version: Mapped[str] = mapped_column(String(32), index=True)
    os_version: Mapped[str] = mapped_column(String(32), index=True)
    device_model: Mapped[str] = mapped_column(String(64), index=True)

    screen: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    props: Mapped[dict] = mapped_column(JSON, default=dict)


Index("ix_events_name_ts", Event.name, Event.ts)


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(32))
    impact: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)

    screen: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)

    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendation: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class ScreenLink(Base):
    __tablename__ = "screen_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    screen: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(256))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
