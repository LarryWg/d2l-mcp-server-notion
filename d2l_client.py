"""
d2l_client.py
Async HTTP client wrapping the D2L Valence REST API.

D2L exposes course data through their "Valence" API.
Docs: https://docs.valence.desire2learn.com/reference.html

Each public function returns plain Python dicts / lists so callers
(mcp_tools.py) can work with them before persisting to the DB.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Shared async client 
# Re-used across requests to benefit from connection pooling.

_client: httpx.AsyncClient | None = None


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.d2l_api_token}",
        "Content-Type": "application/json",
    }


async def get_client() -> httpx.AsyncClient:
    """Return (or lazily create) the shared async HTTP client."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.d2l_base_url,
            headers=_headers(),
            timeout=httpx.Timeout(30.0),
        )
    return _client


async def close_client() -> None:
    """Gracefully close the shared client. Called on app shutdown."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# Internal helpers 

async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Issue an authenticated GET and return parsed JSON.

    Raises httpx.HTTPStatusError on 4xx/5xx responses.
    """
    client = await get_client()
    response = await client.get(path, params=params)
    response.raise_for_status()
    return response.json()


# Public API 

async def fetch_courses() -> list[dict[str, Any]]:
    """Return a list of enrolled courses for the authenticated user.

    D2L endpoint:
        GET /d2l/api/lp/{ver}/enrollments/myenrollments/

    Returns a normalised list:
        [{"org_unit_id": int, "name": str, "code": str, "is_active": bool, ...}]
    """
    # The Valence LP API version — bump this if your instance is newer.
    LP_VER = "1.51"
    raw = await _get(
        f"/d2l/api/lp/{LP_VER}/enrollments/myenrollments/",
        params={"orgUnitTypeId": 3},  # 3 = Course Offering
    )

    courses: list[dict[str, Any]] = []
    for item in raw.get("Items", []):
        org_unit = item.get("OrgUnit", {})
        access = item.get("Access", {})
        courses.append(
            {
                "org_unit_id": org_unit.get("Id"),
                "name": org_unit.get("Name", ""),
                "code": org_unit.get("Code", ""),
                "type": org_unit.get("Type", {}).get("Name", ""),
                "is_active": access.get("IsActive", True),
                "start_date": access.get("StartDate"),
                "end_date": access.get("EndDate"),
            }
        )
    logger.info("Fetched %d courses from D2L", len(courses))
    return courses


async def fetch_assignments(course_id: int) -> list[dict[str, Any]]:
    """Return assignments (dropbox folders) for *course_id*.

    D2L endpoint:
        GET /d2l/api/le/{ver}/{orgUnitId}/dropbox/folders/

    Returns a normalised list:
        [{"assignment_id": int, "name": str, "due_date": str|None, ...}]
    """
    LE_VER = "1.51"
    raw = await _get(f"/d2l/api/le/{LE_VER}/{course_id}/dropbox/folders/")

    assignments: list[dict[str, Any]] = []
    for item in raw:
        grading = item.get("Grading", {}) or {}
        assignments.append(
            {
                "assignment_id": item.get("Id"),
                "name": item.get("Name", ""),
                "instructions": item.get("Instructions", {}).get("Text", ""),
                "due_date": item.get("DueDate"),
                "max_points": grading.get("MaxPoints"),
                "is_hidden": item.get("IsHidden", False),
            }
        )
    logger.info("Fetched %d assignments for course %s", len(assignments), course_id)
    return assignments


async def fetch_quizzes(course_id: int) -> list[dict[str, Any]]:
    """Return quizzes for *course_id*.

    D2L endpoint:
        GET /d2l/api/le/{ver}/{orgUnitId}/quizzes/

    Returns a normalised list.
    """
    LE_VER = "1.51"
    raw = await _get(
        f"/d2l/api/le/{LE_VER}/{course_id}/quizzes/",
        params={"pageSize": 100},
    )

    quizzes: list[dict[str, Any]] = []
    for item in raw.get("Objects", raw if isinstance(raw, list) else []):
        restrictions = item.get("RestrictedByStartDate", {}) or {}
        quizzes.append(
            {
                "quiz_id": item.get("QuizId") or item.get("Id"),
                "name": item.get("Name", ""),
                "instructions": item.get("Instructions", {}).get("Text", "")
                if isinstance(item.get("Instructions"), dict)
                else "",
                "due_date": item.get("DueDate"),
                "time_limit_minutes": (item.get("TimeLimit") or {}).get("IsEnforced")
                and item.get("TimeLimit", {}).get("TimeLimitValue"),
                "attempts_allowed": (item.get("AttemptsAllowed") or {}).get("NumberOfAttemptsAllowed"),
                "is_active": item.get("IsActive", True),
            }
        )
    logger.info("Fetched %d quizzes for course %s", len(quizzes), course_id)
    return quizzes


async def fetch_syllabus(course_id: int) -> dict[str, Any]:
    """Return the course content / syllabus overview for *course_id*.

    D2L endpoint:
        GET /d2l/api/le/{ver}/{orgUnitId}/content/root/

    Returns a dict with the top-level module tree.
    """
    LE_VER = "1.51"
    raw = await _get(f"/d2l/api/le/{LE_VER}/{course_id}/content/root/")
    logger.info("Fetched syllabus for course %s (%d top-level modules)", course_id, len(raw))
    return {"course_id": course_id, "modules": raw}