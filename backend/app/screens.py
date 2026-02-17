from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Event
from .schemas import ScreenMetricsOut

router = APIRouter()


@router.get("/v1/screens/{name}/metrics", response_model=ScreenMetricsOut)
def get_screen_metrics(
    name: str,
    window_hours: int = 24,
    db: Session = Depends(get_db),
) -> ScreenMetricsOut:
    start = datetime.now(UTC) - timedelta(hours=window_hours)
    rows = db.execute(select(Event).where(Event.screen == name, Event.ts >= start)).scalars().all()

    total = len(rows)
    api_errors = [r for r in rows if r.name == "api_error"]
    latencies = [
        float(r.props.get("api_ms"))
        for r in rows
        if isinstance(r.props, dict) and r.props.get("api_ms") is not None
    ]

    p95 = None
    if latencies:
        latencies.sort()
        idx = int(0.95 * (len(latencies) - 1))
        p95 = float(latencies[idx])

    rate = float(len(api_errors) / total) if total else 0.0
    return ScreenMetricsOut(
        screen=name,
        window_hours=window_hours,
        total_events=total,
        api_error_count=len(api_errors),
        api_error_rate=round(rate, 4),
        p95_api_ms=p95,
    )
