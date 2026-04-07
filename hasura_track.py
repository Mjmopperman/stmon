"""
CLI wrapper for Hasura table tracking and relationship creation.

For manual use outside Docker. The app also runs this automatically
on startup via app/hasura_track.py.

Usage:
    python hasura_track.py              # Track tables + create relationships
    python hasura_track.py --dry-run    # Show what would be done
    python hasura_track.py --tables-only # Only track tables, skip relationships
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

# Override DB_HOST to use the local bind address when running outside Docker
# Inside Docker, DB_HOST is "postgres". Locally, we need 127.0.0.1.
os.environ["DB_HOST"] = os.getenv("DB_HOST_BIND", "127.0.0.1")
# Override Hasura URL to use localhost when running outside Docker
os.environ["HASURA_METADATA_URL"] = "http://127.0.0.1:8080/v1/metadata"

from app.hasura_track import (
    _get_db_tables,
    _get_foreign_keys,
    _get_tracked_tables,
    _get_existing_relationships,
    track_untracked_tables,
    create_relationships,
    _relationship_names,
    SKIP_TABLES,
)
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def run(dry_run=False, tables_only=False):
    """Run Hasura tracking from CLI."""
    db_tables = await _get_db_tables()
    db_tables -= SKIP_TABLES

    # Track untracked tables
    try:
        tracked = await _get_tracked_tables()
    except Exception as e:
        print(f"Could not connect to Hasura: {e}")
        print("Make sure Hasura is running (docker compose -f docker-compose.app-local.yml up -d)")
        return

    untracked = db_tables - tracked
    if untracked:
        print(f"Found {len(untracked)} untracked table(s): {', '.join(sorted(untracked))}")
        if dry_run:
            for t in sorted(untracked):
                print(f"  Would track: {t}")
        else:
            await track_untracked_tables(tracked, db_tables)
    else:
        print(f"All {len(db_tables)} tables already tracked in Hasura.")

    if tables_only:
        return

    # Create relationships
    fks = await _get_foreign_keys()
    if not fks:
        print("\nNo foreign keys found.")
        return

    existing_rels = await _get_existing_relationships() if not dry_run else set()
    print(f"\nFound {len(fks)} foreign key(s)")

    if dry_run:
        for fk in fks:
            obj_name, arr_name = _relationship_names(fk)
            print(f"  Would create object rel: {fk['from_table']}.{obj_name} → {fk['to_table']}")
            print(f"  Would create array rel:  {fk['to_table']}.{arr_name} → {fk['from_table']}")
        return

    new_rels = await create_relationships(existing_rels, fks)
    if new_rels:
        print(f"\nCreated {len(new_rels)} new relationship(s).")
    else:
        print("\nAll relationships already exist.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Track tables and create relationships in Hasura")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--tables-only", action="store_true", help="Only track tables, skip relationships")
    args = parser.parse_args()

    if not all([settings.DB_USER, settings.DB_PASSWORD, settings.DB_NAME, settings.HASURA_ADMIN_SECRET]):
        print("Error: DB_USER, DB_PASSWORD, DB_NAME, and HASURA_ADMIN_SECRET must be set in .env")
        sys.exit(1)

    asyncio.run(run(dry_run=args.dry_run, tables_only=args.tables_only))


if __name__ == "__main__":
    main()