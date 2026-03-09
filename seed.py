"""
Seed the database with some data.
"""
import asyncio
from db import AsyncSessionLocal, init_db, Course

async def seed():
    await init_db()
    async with AsyncSessionLocal() as session:
        # course = Course(
        #     name="Test Course",
        #     code="TEST101",
        #     is_active=True,
        #     d2l_org_unit_id=1234567890,
        # )
        course2 = Course(
            name="Tasdfasdf",
            code="TEST1r23r01",
            is_active=True,
            d2l_org_unit_id=123456347890,
        )
        course3 = Course(
            name="Tegaergse",
            code="TESr23rT101",
            is_active=True,
            d2l_org_unit_id=118890,
        )
        course4 = Course(
            name="gaergrse",
            code="TES23r23rT101",
            is_active=True,
            d2l_org_unit_id=12354267890,
        )
        course5 = Course(
            name="Taergrse",
            code="TEST23arg101",
            is_active=True,
            d2l_org_unit_id=123060864567890,
        )

        # session.add(course)   
        session.add(course2)
        session.add(course3)
        session.add(course4)
        session.add(course5)
        await session.commit()
        print("COIURSES ADD!ED")

asyncio.run(seed())