from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

import d2l_client
import mcp_tools
from db import get_db, init_db

# Logging 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# Lifespan (startup / shutdown) 

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run setup before the app starts and teardown when it stops."""
    logger.info("🚀 D2LNOTIONMCP starting up…")
    await init_db()                  # create tables if they don't exist
    logger.info("✅ Database tables ready")
    yield
    await d2l_client.close_client()  # close the shared httpx client
    logger.info("👋 D2LNOTIONMCP shut down cleanly")


# App 

app = FastAPI(
    title="D2LNOTIONMCP",
    description=(
        "MCP-style API server that bridges D2L (Brightspace) and Notion. "
        "Fetch course data, store it in PostgreSQL, and sync it to Notion."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# Health 

@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok", "service": "D2LNOTIONMCP"}


# Courses 

@app.get(
    "/courses",
    tags=["courses"],
    summary="List all courses stored in the database",
    response_description="Array of course objects",
)
async def get_courses(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """Return every course that has been synced from D2L.

    Run `POST /sync/courses` first to populate the database.
    """
    courses = await mcp_tools.list_courses(db)
    return courses


@app.post(
    "/sync/courses",
    tags=["sync"],
    summary="Fetch all courses from D2L and upsert into the database",
    status_code=status.HTTP_200_OK,
)
async def sync_courses(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Pull enrolled courses from the D2L API and persist them to PostgreSQL.

    Existing records are updated; new courses are inserted.
    """
    try:
        courses = await mcp_tools.sync_courses(db)
        return {"synced": len(courses), "courses": courses}
    except Exception as exc:
        logger.exception("Failed to sync courses: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"D2L API error: {exc}",
        )


# Assignments 

@app.get(
    "/assignments/{course_id}",
    tags=["assignments"],
    summary="List assignments for a course",
)
async def get_assignments(
    course_id: int, db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    """Return assignments stored in the database for *course_id* (D2L org unit id)."""
    return await mcp_tools.list_assignments(course_id, db)


@app.post(
    "/sync/{course_id}/assignments",
    tags=["sync"],
    summary="Fetch assignments from D2L and upsert into the database",
)
async def sync_assignments(
    course_id: int, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Pull assignments for *course_id* from D2L and persist them.

    Requires the course to already exist (run `/sync/courses` first).
    """
    try:
        assignments = await mcp_tools.sync_assignments(course_id, db)
        return {"synced": len(assignments), "course_id": course_id, "assignments": assignments}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to sync assignments for course %s: %s", course_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"D2L API error: {exc}",
        )


# Quizzes 

@app.get(
    "/quizzes/{course_id}",
    tags=["quizzes"],
    summary="List quizzes for a course",
)
async def get_quizzes(
    course_id: int, db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    """Return quizzes stored in the database for *course_id*."""
    return await mcp_tools.list_quizzes(course_id, db)


@app.post(
    "/sync/{course_id}/quizzes",
    tags=["sync"],
    summary="Fetch quizzes from D2L and upsert into the database",
)
async def sync_quizzes(
    course_id: int, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Pull quizzes for *course_id* from D2L and persist them."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Quiz sync coming in the next step — assignments first!",
    )


# Syllabus 

@app.get(
    "/syllabus/{course_id}",
    tags=["syllabus"],
    summary="Fetch syllabus directly from D2L (not cached)",
)
async def get_syllabus(course_id: int) -> dict[str, Any]:
    """Return the content module tree for *course_id* straight from D2L."""
    try:
        return await d2l_client.fetch_syllabus(course_id)
    except Exception as exc:
        logger.exception("Failed to fetch syllabus for course %s: %s", course_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"D2L API error: {exc}",
        )


@app.post(
    "/sync/{course_id}/syllabus",
    tags=["sync"],
    summary="Sync syllabus to Notion",
)
async def sync_syllabus(course_id: int) -> dict[str, Any]:
    """Fetch syllabus from D2L and push it to a Notion page (coming soon)."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Notion sync coming in the next step!",
    )