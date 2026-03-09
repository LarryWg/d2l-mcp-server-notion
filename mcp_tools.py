"""
mcp_tools.py
Business logic that sits between the FastAPI routes and the lower-level
clients / DB layer.

Each function corresponds to one MCP-style tool/endpoint.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import d2l_client
from db import Assignment, Course, Quiz

logger = logging.getLogger(__name__)


# ── Courses ───────────────────────────────────────────────────────────────────

async def list_courses(db: AsyncSession) -> list[dict[str, Any]]:
    """Return all courses currently stored in the database."""
    result = await db.execute(select(Course).order_by(Course.name))
    courses = result.scalars().all()
    return [
        {
            "id": c.id,
            "org_unit_id": c.d2l_org_unit_id,
            "name": c.name,
            "code": c.code,
            "is_active": c.is_active,
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "synced_at": c.synced_at.isoformat() if c.synced_at else None,
        }
        for c in courses
    ]


async def sync_courses(db: AsyncSession) -> list[dict[str, Any]]:
    """Fetch courses from D2L and upsert them into the database.

    Returns the list of upserted course dicts.
    """
    raw_courses = await d2l_client.fetch_courses()
    upserted: list[dict[str, Any]] = []

    for raw in raw_courses:
        org_unit_id = raw["org_unit_id"]

        # Try to find an existing record
        result = await db.execute(
            select(Course).where(Course.d2l_org_unit_id == org_unit_id)
        )
        course = result.scalar_one_or_none()

        if course is None:
            course = Course(d2l_org_unit_id=org_unit_id)
            db.add(course)
            logger.info("Inserting new course: %s (id=%s)", raw["name"], org_unit_id)
        else:
            logger.info("Updating existing course: %s (id=%s)", raw["name"], org_unit_id)

        course.name = raw["name"]
        course.code = raw.get("code", "")
        course.is_active = raw.get("is_active", True)

        # Parse ISO-8601 dates if present
        from datetime import datetime, timezone

        def _parse_dt(val: str | None):
            if not val:
                return None
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None

        course.start_date = _parse_dt(raw.get("start_date"))
        course.end_date = _parse_dt(raw.get("end_date"))

        upserted.append(raw)

    await db.flush()  # get generated IDs before commit (commit in get_db)
    logger.info("Synced %d courses from D2L", len(upserted))
    return upserted


# ── Assignments ───────────────────────────────────────────────────────────────

async def list_assignments(course_id: int, db: AsyncSession) -> list[dict[str, Any]]:
    """Return all assignments for a course from the database."""
    # Resolve internal course PK from D2L org unit id
    result = await db.execute(
        select(Course).where(Course.d2l_org_unit_id == course_id)
    )
    course = result.scalar_one_or_none()
    if course is None:
        return []

    result = await db.execute(
        select(Assignment)
        .where(Assignment.course_id == course.id)
        .order_by(Assignment.due_date.asc().nulls_last())
    )
    assignments = result.scalars().all()
    return [
        {
            "id": a.id,
            "assignment_id": a.d2l_assignment_id,
            "course_id": course_id,
            "name": a.name,
            "instructions": a.instructions,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "max_points": a.max_points,
            "notion_page_id": a.notion_page_id,
            "synced_at": a.synced_at.isoformat() if a.synced_at else None,
        }
        for a in assignments
    ]


async def sync_assignments(course_id: int, db: AsyncSession) -> list[dict[str, Any]]:
    """Fetch assignments from D2L and upsert them for *course_id*."""
    from datetime import datetime

    # Resolve course
    result = await db.execute(
        select(Course).where(Course.d2l_org_unit_id == course_id)
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise ValueError(f"Course {course_id} not found in DB. Run /sync/courses first.")

    raw_list = await d2l_client.fetch_assignments(course_id)
    upserted: list[dict[str, Any]] = []

    def _parse_dt(val):
        if not val:
            return None
        try:
            return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    for raw in raw_list:
        d2l_id = raw["assignment_id"]
        result = await db.execute(
            select(Assignment).where(Assignment.d2l_assignment_id == d2l_id)
        )
        assignment = result.scalar_one_or_none()

        if assignment is None:
            assignment = Assignment(d2l_assignment_id=d2l_id, course_id=course.id)
            db.add(assignment)

        assignment.name = raw["name"]
        assignment.instructions = raw.get("instructions", "")
        assignment.due_date = _parse_dt(raw.get("due_date"))
        assignment.max_points = raw.get("max_points")
        upserted.append(raw)

    await db.flush()
    logger.info("Synced %d assignments for course %s", len(upserted), course_id)
    return upserted


# ── Quizzes ───────────────────────────────────────────────────────────────────

async def list_quizzes(course_id: int, db: AsyncSession) -> list[dict[str, Any]]:
    """Return all quizzes for a course from the database."""
    result = await db.execute(
        select(Course).where(Course.d2l_org_unit_id == course_id)
    )
    course = result.scalar_one_or_none()
    if course is None:
        return []

    result = await db.execute(
        select(Quiz)
        .where(Quiz.course_id == course.id)
        .order_by(Quiz.due_date.asc().nulls_last())
    )
    quizzes = result.scalars().all()
    return [
        {
            "id": q.id,
            "quiz_id": q.d2l_quiz_id,
            "course_id": course_id,
            "name": q.name,
            "instructions": q.instructions,
            "due_date": q.due_date.isoformat() if q.due_date else None,
            "time_limit_minutes": q.time_limit_minutes,
            "attempts_allowed": q.attempts_allowed,
            "notion_page_id": q.notion_page_id,
            "synced_at": q.synced_at.isoformat() if q.synced_at else None,
        }
        for q in quizzes
    ]