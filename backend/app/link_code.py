from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import ScreenLink
from .schemas import LinkCodeIn

router = APIRouter()


@router.post("/v1/link-code")
def link_code(payload: LinkCodeIn, db: Session = Depends(get_db)) -> dict[str, str]:
    existing = db.execute(
        select(ScreenLink).where(ScreenLink.screen == payload.screen)
    ).scalar_one_or_none()
    if existing:
        existing.source = payload.source
    else:
        db.add(ScreenLink(screen=payload.screen, source=payload.source))
    db.commit()
    return {"screen": payload.screen, "source": payload.source}
