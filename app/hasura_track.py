"""
Hasura table tracking and relationship creation.

Runs on app startup to ensure all database tables are tracked
in Hasura and foreign key relationships are configured.
"""

import asyncio
import logging

import asyncpg
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Tables that are internal and should not be tracked in Hasura
SKIP_TABLES = {"migrations"}


def _db_host():
    """Use DB_HOST (Docker network hostname) when running inside Docker,
    DB_HOST_BIND (127.0.0.1) when running locally."""
    return settings.DB_HOST


async def _hasura_api(payload: dict) -> httpx.Response:
    """Call the Hasura Metadata API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.HASURA_METADATA_URL,
            headers={
                "Content-Type": "application/json",
                "X-Hasura-Admin-Secret": settings.HASURA_ADMIN_SECRET,
            },
            json=payload,
            timeout=30.0,
        )
    return response


async def _get_db_tables() -> set:
    """Get all user tables from the database."""
    conn = await asyncpg.connect(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        host=_db_host(),
        port=settings.DB_PORT,
    )
    try:
        rows = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        return {r["tablename"] for r in rows}
    finally:
        await conn.close()


async def _get_foreign_keys() -> list:
    """Get all foreign key relationships from the database."""
    conn = await asyncpg.connect(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        host=_db_host(),
        port=settings.DB_PORT,
    )
    try:
        rows = await conn.fetch("""
            SELECT
                tc.table_name AS from_table,
                kcu.column_name AS from_column,
                ccu.table_name AS to_table,
                ccu.column_name AS to_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
        """)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def _get_tracked_tables() -> set:
    """Get tables already tracked in Hasura."""
    response = await _hasura_api({"type": "export_metadata", "args": {}})
    response.raise_for_status()
    metadata = response.json()

    tracked = set()
    for source in metadata.get("sources", []):
        for table in source.get("tables", []):
            tracked.add(table["table"]["name"])
    return tracked


async def _get_existing_relationships() -> set:
    """Get relationships already defined in Hasura."""
    response = await _hasura_api({"type": "export_metadata", "args": {}})
    response.raise_for_status()
    metadata = response.json()

    existing = set()
    for source in metadata.get("sources", []):
        for table in source.get("tables", []):
            table_name = table["table"]["name"]
            for rel in table.get("object_relationships", []):
                existing.add(("object", table_name, rel["name"]))
            for rel in table.get("array_relationships", []):
                existing.add(("array", table_name, rel["name"]))
    return existing


def _relationship_names(fk: dict) -> tuple:
    """Generate relationship names from a foreign key.

    Returns (object_rel_name, array_rel_name).
    e.g. orders.user_id → users.id gives:
      - object: "user" on orders
      - array: "orders" on users
    """
    from_column = fk["from_column"]
    to_table = fk["to_table"]
    from_table = fk["from_table"]

    # Object relationship: from_table → to_table
    # Name based on the FK column without _id suffix
    if from_column.endswith("_id"):
        obj_name = from_column[:-3]
    else:
        obj_name = to_table

    # Array relationship: to_table → from_table
    arr_name = from_table

    return obj_name, arr_name


async def track_untracked_tables(tracked: set, db_tables: set) -> list:
    """Track tables in Hasura that aren't already tracked."""
    untracked = db_tables - tracked - SKIP_TABLES
    if not untracked:
        return []

    tracked_names = []
    for table in sorted(untracked):
        response = await _hasura_api({
            "type": "pg_track_table",
            "args": {"source": "default", "table": table},
        })
        if response.status_code == 200:
            logger.info(f"Hasura: tracked table {table}")
            tracked_names.append(table)
        elif "already tracked" in response.text:
            tracked_names.append(table)
        else:
            logger.warning(f"Hasura: error tracking {table}: {response.text}")

    return tracked_names


async def create_relationships(existing_rels: set, fks: list) -> list:
    """Create object and array relationships from foreign keys."""
    created = []

    for fk in fks:
        from_table = fk["from_table"]
        to_table = fk["to_table"]
        obj_name, arr_name = _relationship_names(fk)

        # Object relationship (many-to-one)
        obj_key = ("object", from_table, obj_name)
        if obj_key not in existing_rels:
            response = await _hasura_api({
                "type": "pg_create_object_relationship",
                "args": {
                    "source": "default",
                    "table": from_table,
                    "name": obj_name,
                    "using": {"foreign_key_constraint_on": fk["from_column"]},
                },
            })
            if response.status_code == 200:
                logger.info(f"Hasura: object rel {from_table}.{obj_name} → {to_table}")
                created.append(obj_key)
            elif "already exists" in response.text:
                pass
            else:
                logger.warning(f"Hasura: error creating object rel {from_table}.{obj_name}: {response.text}")

        # Array relationship (one-to-many)
        arr_key = ("array", to_table, arr_name)
        if arr_key not in existing_rels:
            response = await _hasura_api({
                "type": "pg_create_array_relationship",
                "args": {
                    "source": "default",
                    "table": to_table,
                    "name": arr_name,
                    "using": {
                        "foreign_key_constraint_on": {
                            "table": from_table,
                            "column": fk["from_column"],
                        },
                    },
                },
            })
            if response.status_code == 200:
                logger.info(f"Hasura: array rel {to_table}.{arr_name} → {from_table}")
                created.append(arr_key)
            elif "already exists" in response.text:
                pass
            else:
                logger.warning(f"Hasura: error creating array rel {to_table}.{arr_name}: {response.text}")

    return created


async def run_hasura_track():
    """Track untracked tables and create relationships in Hasura.

    Called from FastAPI startup. Non-fatal: logs warnings on failure.
    Retries up to 6 times with a 5-second delay to handle Hasura startup timing.
    """
    for attempt in range(6):
        try:
            db_tables = await _get_db_tables()
            tracked = await _get_tracked_tables()

            # Track new tables
            new_tables = await track_untracked_tables(tracked, db_tables)
            if new_tables:
                logger.info(f"Hasura: tracked {len(new_tables)} new table(s)")
            else:
                logger.info("Hasura: all tables already tracked")

            # Create relationships
            fks = await _get_foreign_keys()
            existing_rels = await _get_existing_relationships()
            new_rels = await create_relationships(existing_rels, fks)
            if new_rels:
                logger.info(f"Hasura: created {len(new_rels)} new relationship(s)")
            else:
                logger.info("Hasura: all relationships already exist")

            return

        except Exception as e:
            if attempt < 5:
                logger.warning(f"Hasura track attempt {attempt + 1} failed: {e}. Retrying in 5s...")
                await asyncio.sleep(5)
            else:
                logger.error(f"Hasura track failed after 6 attempts: {e}")