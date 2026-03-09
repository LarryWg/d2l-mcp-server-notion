# """
# tests/test_assignments.py
# Tests for GET /assignments/{course_id} and POST /sync/{course_id}/assignments.
# """

# from __future__ import annotations

# from unittest.mock import AsyncMock, patch

# import pytest
# from httpx import AsyncClient
# from sqlalchemy.ext.asyncio import AsyncSession

# from db import Course
# from tests.conftest import MOCK_ASSIGNMENTS, MOCK_COURSES


# async def _seed_course(db_session: AsyncSession, org_unit_id: int = 101) -> Course:
#     """Helper: insert a course row and return it."""
#     course = Course(
#         d2l_org_unit_id=org_unit_id,
#         name="Introduction to Machine Learning",
#         code="CS4ML",
#         is_active=True,
#     )
#     db_session.add(course)
#     await db_session.commit()
#     await db_session.refresh(course)
#     return course


# # ── GET /assignments/{course_id} ──────────────────────────────────────────────

# @pytest.mark.asyncio
# async def test_get_assignments_empty(client: AsyncClient, db_session: AsyncSession):
#     """Should return empty list when course has no assignments yet."""
#     await _seed_course(db_session)
#     response = await client.get("/assignments/101")
#     assert response.status_code == 200
#     assert response.json() == []


# @pytest.mark.asyncio
# async def test_get_assignments_unknown_course(client: AsyncClient):
#     """Should return empty list (not 404) for an unknown course id."""
#     response = await client.get("/assignments/9999")
#     assert response.status_code == 200
#     assert response.json() == []


# # ── POST /sync/{course_id}/assignments ────────────────────────────────────────

# @pytest.mark.asyncio
# async def test_sync_assignments_success(client: AsyncClient, db_session: AsyncSession):
#     """Should fetch from D2L and persist assignments."""
#     await _seed_course(db_session)

#     with patch(
#         "mcp_tools.d2l_client.fetch_assignments", new_callable=AsyncMock
#     ) as mock_fetch:
#         mock_fetch.return_value = MOCK_ASSIGNMENTS
#         response = await client.post("/sync/101/assignments")

#     assert response.status_code == 200
#     data = response.json()
#     assert data["synced"] == 2
#     assert data["course_id"] == 101

#     # Assignments should now be readable
#     get_resp = await client.get("/assignments/101")
#     assignments = get_resp.json()
#     assert len(assignments) == 2
#     names = {a["name"] for a in assignments}
#     assert "Linear Regression Implementation" in names
#     assert "Neural Network Report" in names


# @pytest.mark.asyncio
# async def test_sync_assignments_without_course_sync_first(client: AsyncClient):
#     """Should return 404 if course doesn't exist in DB yet."""
#     with patch(
#         "mcp_tools.d2l_client.fetch_assignments", new_callable=AsyncMock
#     ) as mock_fetch:
#         mock_fetch.return_value = MOCK_ASSIGNMENTS
#         response = await client.post("/sync/101/assignments")

#     assert response.status_code == 404
#     assert "not found" in response.json()["detail"].lower()


# @pytest.mark.asyncio
# async def test_sync_assignments_is_idempotent(client: AsyncClient, db_session: AsyncSession):
#     """Syncing assignments twice should not create duplicates."""
#     await _seed_course(db_session)

#     with patch(
#         "mcp_tools.d2l_client.fetch_assignments", new_callable=AsyncMock
#     ) as mock_fetch:
#         mock_fetch.return_value = MOCK_ASSIGNMENTS
#         await client.post("/sync/101/assignments")
#         await client.post("/sync/101/assignments")

#     get_resp = await client.get("/assignments/101")
#     assert len(get_resp.json()) == 2  # still 2, not 4


# @pytest.mark.asyncio
# async def test_sync_assignments_due_dates_parsed(
#     client: AsyncClient, db_session: AsyncSession
# ):
#     """Due dates from D2L should be stored and returned as ISO strings."""
#     await _seed_course(db_session)

#     with patch(
#         "mcp_tools.d2l_client.fetch_assignments", new_callable=AsyncMock
#     ) as mock_fetch:
#         mock_fetch.return_value = [MOCK_ASSIGNMENTS[0]]
#         await client.post("/sync/101/assignments")

#     assignments = (await client.get("/assignments/101")).json()
#     assert assignments[0]["due_date"] is not None
#     assert "2025-02-15" in assignments[0]["due_date"]