from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .db import get_db
from .models import Event
from .schemas import EventBatchIn

router = APIRouter()


@router.post("/v1/events/batch")
def ingest_events(payload: EventBatchIn, db: Session = Depends(get_db)) -> dict[str, int]:
    rows = [
        Event(
            event_id=e.event_id,
            name=e.name,
            ts=e.ts,
            user_id=e.user_id,
            session_id=e.session_id,
            platform=e.platform,
            app_version=e.app_version,
            os_version=e.os_version,
            device_model=e.device_model,
            screen=e.screen,
            source=e.source,
            props=e.props,
        )
        for e in payload.events
    ]
    db.add_all(rows)
    db.commit()
    return {"ingested": len(rows)}
