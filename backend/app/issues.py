from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Issue
from .schemas import IssueOut, RecommendationOut

router = APIRouter()


@router.get("/v1/issues", response_model=list[IssueOut])
def list_issues(limit: int = 50, db: Session = Depends(get_db)) -> list[Issue]:
    query = select(Issue).order_by(desc(Issue.created_at)).limit(limit)
    return db.execute(query).scalars().all()


@router.get("/v1/issues/{key}", response_model=IssueOut)
def get_issue(key: str, db: Session = Depends(get_db)) -> Issue:
    issue = db.execute(select(Issue).where(Issue.key == key)).scalar_one_or_none()
    if not issue:
        raise HTTPException(404, "Issue not found")
    return issue


@router.get("/v1/recommendations", response_model=list[RecommendationOut])
def list_recommendations(limit: int = 50, db: Session = Depends(get_db)) -> list[RecommendationOut]:
    issues = db.execute(select(Issue).order_by(desc(Issue.created_at)).limit(limit)).scalars().all()
    return [
        RecommendationOut(
            issue_key=item.key,
            title=item.title,
            recommendation=item.recommendation or {},
            confidence=item.confidence,
        )
        for item in issues
    ]
