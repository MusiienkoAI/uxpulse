from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    event_id: str
    name: str
    ts: datetime
    user_id: str
    session_id: str
    platform: str
    app_version: str
    os_version: str
    device_model: str
    screen: str | None = None
    source: str | None = None
    props: dict[str, Any] = Field(default_factory=dict)


class EventBatchIn(BaseModel):
    events: list[EventIn]


class IssueOut(BaseModel):
    id: int
    key: str
    title: str
    category: str
    impact: str
    confidence: float
    screen: str | None = None
    source: str | None = None
    evidence: dict[str, Any]
    recommendation: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ScreenMetricsOut(BaseModel):
    screen: str
    window_hours: int
    total_events: int
    api_error_count: int
    api_error_rate: float
    p95_api_ms: float | None = None


class RecommendationOut(BaseModel):
    issue_key: str
    title: str
    recommendation: dict[str, Any]
    confidence: float


class LinkCodeIn(BaseModel):
    screen: str
    source: str


class AnalyzedIssueOut(BaseModel):
    key: str
    title: str
    category: str
    impact: str
    confidence: float = Field(ge=0.0, le=1.0)
    screen: str | None = None
    source: str | None = None
    evidence: dict[str, Any]
    recommendation: dict[str, Any]
    created_at: datetime
