import json
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://uxpulse:uxpulse@localhost:5432/uxpulse",
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
MIN_EVENTS_FOR_ISSUE = int(os.getenv("MIN_EVENTS_FOR_ISSUE", "5"))


def upsert_issue(
    db: Session,
    key: str,
    title: str,
    category: str,
    impact: str,
    confidence: float,
    screen: str | None,
    source: str | None,
    evidence: dict,
    recommendation: dict,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO issues (
              key, title, category, impact, confidence, screen, source, evidence, recommendation, created_at
            )
            VALUES (
              :key, :title, :category, :impact, :confidence, :screen, :source, CAST(:evidence AS jsonb), CAST(:recommendation AS jsonb), :created_at
            )
            ON CONFLICT (key) DO UPDATE SET
              title = EXCLUDED.title,
              category = EXCLUDED.category,
              impact = EXCLUDED.impact,
              confidence = EXCLUDED.confidence,
              screen = EXCLUDED.screen,
              source = EXCLUDED.source,
              evidence = EXCLUDED.evidence,
              recommendation = EXCLUDED.recommendation,
              created_at = EXCLUDED.created_at
            """
        ),
        {
            "key": key,
            "title": title,
            "category": category,
            "impact": impact,
            "confidence": confidence,
            "screen": screen,
            "source": source,
            "evidence": json.dumps(evidence),
            "recommendation": json.dumps(recommendation),
            "created_at": datetime.now(UTC),
        },
    )


def main() -> None:
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=24)

    with Session(engine) as db:
        rows = db.execute(
            text(
                """
                SELECT
                  COALESCE(screen, '(unknown)') AS screen,
                  MAX(source) AS source,
                  COUNT(*) FILTER (WHERE name='api_error')::float / NULLIF(COUNT(*), 0) AS error_rate,
                  COUNT(*) FILTER (WHERE name='api_error') AS errors,
                  COUNT(*) AS total
                FROM events
                WHERE ts >= :window_start
                GROUP BY COALESCE(screen, '(unknown)')
                HAVING COUNT(*) >= :min_events
                ORDER BY error_rate DESC
                LIMIT 8
                """
            ),
            {"window_start": window_start, "min_events": MIN_EVENTS_FOR_ISSUE},
        ).all()

        for screen, source, error_rate, errors, total in rows:
            if error_rate is None:
                continue

            impact = "high" if error_rate >= 0.15 else "medium" if error_rate >= 0.07 else "low"
            key = f"reliability:{screen}:24h"
            error_rate_val = round(float(error_rate), 4)

            evidence = {
                "window_hours": 24,
                "error_rate": error_rate_val,
                "errors": int(errors),
                "total_events": int(total),
            }
            recommendation = {
                "hypothesis": "API failures correlate with checkout abandonment.",
                "suggested_fixes": [
                    "Add retry/backoff for transient errors",
                    "Add timeout-specific UX feedback",
                    "Capture endpoint + latency instrumentation",
                ],
                "experiment": {
                    "variantA": "Current error handling",
                    "variantB": "Retry + explicit user messaging",
                    "primaryMetric": "checkout_completion_rate",
                },
            }
            title = f"High API error rate on {screen} ({error_rate_val * 100:.1f}%)"

            upsert_issue(
                db=db,
                key=key,
                title=title,
                category="reliability",
                impact=impact,
                confidence=0.65,
                screen=None if screen == "(unknown)" else screen,
                source=source,
                evidence=evidence,
                recommendation=recommendation,
            )

        db.commit()


if __name__ == "__main__":
    main()
