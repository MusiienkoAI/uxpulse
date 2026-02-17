import json
import os
from datetime import UTC, datetime, timedelta
from hashlib import sha1
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from openai import OpenAI
from openai import OpenAIError
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db
from .schemas import AnalyzedIssueOut

load_dotenv()

router = APIRouter()


@router.get("/v1/issues/analyze", response_model=list[AnalyzedIssueOut])
def analyze_issues_with_llm(
    screen: str | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
) -> list[AnalyzedIssueOut]:
    provider = os.getenv("FOUNDATION_MODEL_PROVIDER", "openai").strip().lower()
    if provider != "openai":
        raise HTTPException(
            status_code=400,
            detail="FOUNDATION_MODEL_PROVIDER must be 'openai' for this endpoint.",
        )

    api_key = os.getenv("FOUNDATION_MODEL_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="FOUNDATION_MODEL_API_KEY is missing. Set it in your .env file.",
        )

    model_name = os.getenv("FOUNDATION_MODEL_NAME", "gpt-4o-mini")
    base_url = os.getenv("FOUNDATION_MODEL_BASE_URL", "").strip() or None
    client = OpenAI(api_key=api_key, base_url=base_url)

    metrics = _load_screen_metrics(db=db, hours=hours, screen=screen)
    if not metrics:
        return []

    llm_cards = _generate_cards(client=client, model_name=model_name, hours=hours, metrics=metrics)
    now = datetime.now(UTC)

    cards: list[AnalyzedIssueOut] = []
    for item in llm_cards:
        screen_name = item.get("screen")
        metrics_item = next((m for m in metrics if m["screen"] == screen_name), None)
        if not metrics_item:
            continue

        issue_key = _make_issue_key(screen_name=screen_name, hours=hours, evidence=metrics_item)
        cards.append(
            AnalyzedIssueOut(
                key=issue_key,
                title=str(item.get("title", "Screen UX issue detected")),
                category=str(item.get("category", "ux")),
                impact=str(item.get("impact", "medium")),
                confidence=float(item.get("confidence", 0.5)),
                screen=screen_name,
                source=metrics_item.get("source"),
                evidence=metrics_item,
                recommendation={
                    "hypothesis": item.get("hypothesis", ""),
                    "suggested_fixes": item.get("suggested_fixes", []),
                    "experiment": item.get("experiment", {}),
                },
                created_at=now,
            )
        )

    return cards


def _load_screen_metrics(db: Session, hours: int, screen: str | None) -> list[dict[str, Any]]:
    window_start = datetime.now(UTC) - timedelta(hours=hours)
    params: dict[str, Any] = {"window_start": window_start}
    screen_filter = ""
    if screen:
        screen_filter = "AND screen = :screen"
        params["screen"] = screen

    rows = db.execute(
        text(
            f"""
            SELECT
              COALESCE(screen, '(unknown)') AS screen,
              MAX(source) FILTER (WHERE source IS NOT NULL) AS source,
              COUNT(*) AS total_events,
              COUNT(*) FILTER (WHERE name='api_error') AS api_error_count,
              COUNT(*) FILTER (WHERE name='api_ok') AS api_ok_count,
              COUNT(*) FILTER (WHERE name='screen_view') AS screen_view_count,
              COUNT(*) FILTER (WHERE name='add_to_cart') AS add_to_cart_count,
              COUNT(*) FILTER (WHERE name='checkout_complete') AS checkout_complete_count,
              ROUND(
                (COUNT(*) FILTER (WHERE name='api_error')::numeric / NULLIF(COUNT(*), 0)),
                4
              ) AS api_error_rate,
              percentile_cont(0.95) WITHIN GROUP (ORDER BY (props->>'api_ms')::numeric)
                FILTER (WHERE (props::jsonb ? 'api_ms')) AS p95_api_ms
            FROM events
            WHERE ts >= :window_start
              {screen_filter}
            GROUP BY COALESCE(screen, '(unknown)')
            ORDER BY total_events DESC
            """
        ),
        params,
    ).mappings().all()

    result: list[dict[str, Any]] = []
    for row in rows:
        screen_name = str(row["screen"])
        endpoints = db.execute(
            text(
                """
                SELECT
                  props->>'endpoint' AS endpoint,
                  COUNT(*) FILTER (WHERE name='api_error') AS api_errors,
                  COUNT(*) FILTER (WHERE name='api_ok') AS api_success
                FROM events
                WHERE ts >= :window_start
                  AND COALESCE(screen, '(unknown)') = :screen_name
                  AND (props::jsonb ? 'endpoint')
                GROUP BY props->>'endpoint'
                ORDER BY api_errors DESC, api_success DESC
                LIMIT 3
                """
            ),
            {"window_start": window_start, "screen_name": screen_name},
        ).mappings().all()

        result.append(
            {
                "window_hours": hours,
                "screen": screen_name,
                "source": row["source"],
                "total_events": int(row["total_events"]),
                "api_error_count": int(row["api_error_count"]),
                "api_ok_count": int(row["api_ok_count"]),
                "screen_view_count": int(row["screen_view_count"]),
                "add_to_cart_count": int(row["add_to_cart_count"]),
                "checkout_complete_count": int(row["checkout_complete_count"]),
                "api_error_rate": float(row["api_error_rate"] or 0.0),
                "p95_api_ms": float(row["p95_api_ms"]) if row["p95_api_ms"] is not None else None,
                "top_endpoints": [
                    {
                        "endpoint": endpoint_row["endpoint"],
                        "api_errors": int(endpoint_row["api_errors"]),
                        "api_success": int(endpoint_row["api_success"]),
                    }
                    for endpoint_row in endpoints
                ],
            }
        )
    return result


def _generate_cards(client: OpenAI, model_name: str, hours: int, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prompt = {
        "task": "Generate UX issue cards from screen metrics.",
        "rules": [
            "Use only the provided metrics. Do not invent numeric values.",
            "Return one issue per screen that has notable risk or degradation signal.",
            "confidence must be a float between 0 and 1.",
            "impact must be one of: high, medium, low.",
            "category should be one of: ux, performance, reliability, funnel.",
        ],
        "window_hours": hours,
        "metrics": metrics,
        "output_schema": {
            "issues": [
                {
                    "screen": "string",
                    "title": "string",
                    "category": "ux|performance|reliability|funnel",
                    "impact": "high|medium|low",
                    "confidence": "number_0_to_1",
                    "hypothesis": "string",
                    "suggested_fixes": ["string"],
                    "experiment": {
                        "variantA": "string",
                        "variantB": "string",
                        "primaryMetric": "string",
                    },
                }
            ]
        },
    }

    try:
        completion = client.chat.completions.create(
            model=model_name,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior product analytics assistant. "
                        "Generate concise, evidence-driven issue cards. "
                        "Return strict JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Respond in JSON matching the requested schema.\n"
                        + json.dumps(prompt)
                    ),
                },
            ],
        )
    except OpenAIError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {exc}") from exc

    content = completion.choices[0].message.content
    if not content:
        raise HTTPException(status_code=502, detail="OpenAI returned empty content.")

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to parse OpenAI JSON: {exc}") from exc

    issues = payload.get("issues")
    if not isinstance(issues, list):
        raise HTTPException(status_code=502, detail="OpenAI payload missing 'issues' array.")
    return [item for item in issues if isinstance(item, dict)]


def _make_issue_key(screen_name: str | None, hours: int, evidence: dict[str, Any]) -> str:
    stable_source = {
        "screen": screen_name or "(unknown)",
        "hours": hours,
        "total_events": evidence.get("total_events"),
        "api_error_count": evidence.get("api_error_count"),
        "api_error_rate": evidence.get("api_error_rate"),
        "p95_api_ms": evidence.get("p95_api_ms"),
    }
    digest = sha1(json.dumps(stable_source, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"llm:{stable_source['screen']}:{hours}h:{digest}"
