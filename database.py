"""
TimeTrack persistence layer.

Async MySQL database hosted on Filess.io.

Both the FastAPI REST API and MCP server use these
same database functions.
"""

import os
from pathlib import Path

import aiomysql
from dotenv import load_dotenv

# Load .env from the project root
# BASE_DIR = Path(__file__).resolve().parent
# load_dotenv(BASE_DIR / ".env")

load_dotenv()


# ---------------------------------------------------------
# Database configuration
# ---------------------------------------------------------

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3307"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")


# ---------------------------------------------------------
# Get async MySQL connection
# ---------------------------------------------------------

async def get_connection():
   
    return await aiomysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        db=MYSQL_DATABASE,
        cursorclass=aiomysql.DictCursor,
        autocommit=False,
    )


# ---------------------------------------------------------
# Initialize database
# ---------------------------------------------------------

async def init_db():

    connection = await get_connection()

    try:
        cursor = await connection.cursor(aiomysql.DictCursor)

        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id INT PRIMARY KEY AUTO_INCREMENT,
                employee_name VARCHAR(255) NOT NULL,
                project VARCHAR(255) NOT NULL,
                entry_date DATE NOT NULL,
                hours DOUBLE NOT NULL,
                description TEXT NOT NULL
            )
        """)

        await connection.commit()

        # Check if table already contains data
        await cursor.execute(
            "SELECT COUNT(*) AS count FROM time_entries"
        )

        result = await cursor.fetchone()

        count = result["count"]

        # Seed initial data
        if count == 0:

            seed = [
                (
                    "Asha Patel",
                    "Website Redesign",
                    "2026-09-08",
                    6.5,
                    "Homepage layout",
                ),
                (
                    "Asha Patel",
                    "Website Redesign",
                    "2026-09-09",
                    7.0,
                    "Mobile responsive fixes",
                ),
                (
                    "Asha Patel",
                    "Client Onboarding",
                    "2026-09-10",
                    3.0,
                    "Kickoff call + notes",
                ),
                (
                    "Rahul Mehta",
                    "Website Redesign",
                    "2026-09-08",
                    5.5,
                    "API integration",
                ),
                (
                    "Rahul Mehta",
                    "Internal Tools",
                    "2026-09-09",
                    8.0,
                    "Dashboard bug fixes",
                ),
            ]

            await cursor.executemany(
                """
                INSERT INTO time_entries
                (
                    employee_name,
                    project,
                    entry_date,
                    hours,
                    description
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                seed,
            )

            await connection.commit()

    finally:
        await cursor.close()
        connection.close()


# ---------------------------------------------------------
# Convert database row to dictionary
# ---------------------------------------------------------

def _row_to_dict(row) -> dict:

    return {
        "id": row["id"],
        "employee_name": row["employee_name"],
        "project": row["project"],
        "entry_date": str(row["entry_date"]),
        "hours": float(row["hours"]),
        "description": row["description"],
    }


# ---------------------------------------------------------
# List all entries
# ---------------------------------------------------------

async def list_all_entries() -> list[dict]:

    connection = await get_connection()

    try:

        cursor = await connection.cursor(aiomysql.DictCursor)

        await cursor.execute("""
            SELECT *
            FROM time_entries
            ORDER BY entry_date DESC, id DESC
        """)

        rows = await cursor.fetchall()

        return [_row_to_dict(row) for row in rows]

    finally:

        cursor.close()
        connection.close()


# ---------------------------------------------------------
# Log time
# ---------------------------------------------------------

async def log_time(
    employee_name: str,
    project: str,
    entry_date: str,
    hours: float,
    description: str = "",
) -> dict:

    if hours <= 0:
        raise ValueError("hours must be a positive number")

    connection = await get_connection()

    try:

        cursor = await connection.cursor(aiomysql.DictCursor)

        await cursor.execute(
            """
            INSERT INTO time_entries
            (
                employee_name,
                project,
                entry_date,
                hours,
                description
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                employee_name,
                project,
                entry_date,
                hours,
                description,
            ),
        )

        await connection.commit()

        new_id = cursor.lastrowid

        await cursor.execute(
            """
            SELECT *
            FROM time_entries
            WHERE id = %s
            """,
            (new_id,),
        )

        row = await cursor.fetchone()

        return _row_to_dict(row)

    except Exception:

        await connection.rollback()
        raise

    finally:

        cursor.close()
        connection.close()


# ---------------------------------------------------------
# Get employee timesheet
# ---------------------------------------------------------

async def get_timesheet(
    employee_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:

    connection = await get_connection()

    try:

        cursor = await connection.cursor(aiomysql.DictCursor)

        query = """
            SELECT *
            FROM time_entries
            WHERE employee_name = %s
        """

        params = [employee_name]

        if start_date:

            query += " AND entry_date >= %s"
            params.append(start_date)

        if end_date:

            query += " AND entry_date <= %s"
            params.append(end_date)

        query += " ORDER BY entry_date"

        await cursor.execute(query, params)

        rows = await cursor.fetchall()

        return [_row_to_dict(row) for row in rows]

    finally:

        cursor.close()
        connection.close()


# ---------------------------------------------------------
# Execute SELECT query
# ---------------------------------------------------------

async def execute_query(
    query: str,
    params: list | None = None,
) -> list[dict]:

    connection = await get_connection()

    try:

        cursor = await connection.cursor(aiomysql.DictCursor)

        await cursor.execute(
            query,
            params or [],
        )

        rows = await cursor.fetchall()

        return [_row_to_dict(row) for row in rows]

    finally:

        cursor.close()
        connection.close()


# ---------------------------------------------------------
# List projects
# ---------------------------------------------------------

async def list_projects() -> list[str]:

    connection = await get_connection()

    try:

        cursor = await connection.cursor(aiomysql.DictCursor)

        await cursor.execute("""
            SELECT DISTINCT project
            FROM time_entries
            ORDER BY project
        """)

        rows = await cursor.fetchall()

        return [
            row["project"]
            for row in rows
        ]

    finally:

        cursor.close()
        connection.close()


# ---------------------------------------------------------
# Project summary
# ---------------------------------------------------------

async def get_project_summary(
    project: str,
) -> dict:

    connection = await get_connection()

    try:

        cursor = await connection.cursor(aiomysql.DictCursor)

        await cursor.execute(
            """
            SELECT
                employee_name,
                SUM(hours) AS total_hours
            FROM time_entries
            WHERE project = %s
            GROUP BY employee_name
            ORDER BY employee_name
            """,
            (project,),
        )

        rows = await cursor.fetchall()

        if not rows:

            raise ValueError(
                f"No time logged against project '{project}'"
            )

        by_employee = {
            row["employee_name"]:
                float(row["total_hours"])
            for row in rows
        }

        return {
            "project": project,
            "total_hours": sum(
                by_employee.values()
            ),
            "by_employee": by_employee,
        }

    finally:

        cursor.close()
        connection.close()