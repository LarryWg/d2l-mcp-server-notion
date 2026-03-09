"""
Seed the database with some data.
"""
import asyncio
from db import AsyncSessionLocal, init_db, Course

async def seed():
    await init_db()
    async with AsyncSessionLocal() as session:
        course = Course(
            name="Test Course",
            code="TEST101",
            is_active=True,
            d2l_org_unit_id=1234567890,
        )
        session.add(course)
        await session.commit()
        print("COIURSES ADD!ED")

asyncio.run(seed())