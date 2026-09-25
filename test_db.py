import asyncio

import database as db


async def main():

    await db.init_db()

    print("Database initialized successfully.")

    projects = await db.list_projects()

    print("Projects:")
    print(projects)


asyncio.run(main())