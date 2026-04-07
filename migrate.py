"""
Local database migration runner.

Applies pending SQL migrations from db/migrations/ against the local
PostgreSQL database, tracking applied migrations in the migrations table.
Mirrors the same logic used by the GitHub Actions remote deploy.

Usage:
    python migrate.py              # Apply pending migrations
    python migrate.py --status    # Show applied and pending migrations
    python migrate.py --dry-run   # Show what would be applied without running
"""

import os
import sys
import asyncio
from pathlib import Path

import asyncpg

# Load .env
from dotenv import load_dotenv
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST_BIND", os.getenv("DB_HOST", "localhost"))
DB_PORT = int(os.getenv("DB_PORT", "5432"))

MIGRATIONS_DIR = Path(os.getenv("MIGRATIONS_DIR", "db/migrations"))


async def get_connection():
    """Get an async database connection."""
    return await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
    )


async def ensure_migrations_table(conn):
    """Create the migrations tracking table if it doesn't exist."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ DEFAULT now()
        )
    """)


async def get_applied(conn) -> set:
    """Get set of already-applied migration filenames."""
    rows = await conn.fetch("SELECT filename FROM migrations")
    return {r["filename"] for r in rows}


def get_migration_files() -> list:
    """Get sorted list of migration SQL files."""
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def split_sql(sql: str) -> list:
    """Split SQL into individual statements, respecting quotes and comments."""
    statements = []
    current = []
    in_single_quote = False
    in_double_quote = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        # Handle single-quoted strings
        if ch == "'" and not in_double_quote:
            if in_single_quote and i + 1 < len(sql) and sql[i + 1] == "'":
                # Escaped quote ''
                current.append("''")
                i += 2
                continue
            in_single_quote = not in_single_quote
            current.append(ch)
        # Handle double-quoted identifiers
        elif ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(ch)
        # Semicolon outside quotes = statement boundary
        elif ch == ';' and not in_single_quote and not in_double_quote:
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(ch)
        i += 1
    # Catch any trailing statement without semicolon
    stmt = ''.join(current).strip()
    if stmt:
        statements.append(stmt)
    return statements


async def apply_migration(conn, filepath: Path):
    """Apply a single migration file and record it."""
    sql = filepath.read_text(encoding="utf-8")
    filename = filepath.name
    statements = split_sql(sql)

    async with conn.transaction():
        for stmt in statements:
            # Skip comment-only lines
            stripped = stmt.strip()
            if stripped.startswith('--') and '\n' not in stripped.lstrip('-'):
                continue
            if not stripped:
                continue
            await conn.execute(stmt)
        await conn.execute(
            "INSERT INTO migrations (filename) VALUES ($1) ON CONFLICT DO NOTHING",
            filename,
        )


async def run_migrations(dry_run=False):
    """Apply all pending migrations."""
    conn = await get_connection()
    try:
        await ensure_migrations_table(conn)
        applied = await get_applied(conn)
        files = get_migration_files()

        if not files:
            print("No migration files found.")
            return

        pending = [f for f in files if f.name not in applied]

        if not pending:
            print("All migrations already applied.")
            return

        for filepath in pending:
            if dry_run:
                print(f"  Would apply: {filepath.name}")
            else:
                print(f"Applying: {filepath.name}")
                await apply_migration(conn, filepath)
                print(f"  Applied: {filepath.name}")

        if dry_run:
            print(f"\n{len(pending)} migration(s) would be applied.")
        else:
            print(f"\n{len(pending)} migration(s) applied.")
    finally:
        await conn.close()


async def show_status():
    """Show migration status."""
    conn = await get_connection()
    try:
        await ensure_migrations_table(conn)
        applied = await get_applied(conn)
        files = get_migration_files()

        if not files:
            print("No migration files found.")
            return

        for filepath in files:
            if filepath.name in applied:
                print(f"  Applied:   {filepath.name}")
            else:
                print(f"  Pending:   {filepath.name}")

        applied_count = sum(1 for f in files if f.name in applied)
        print(f"\n{applied_count} applied, {len(files) - applied_count} pending.")
    finally:
        await conn.close()


async def mark_applied(filenames: list):
    """Mark migrations as applied without running them (for bootstrap)."""
    conn = await get_connection()
    try:
        await ensure_migrations_table(conn)
        for filename in filenames:
            await conn.execute(
                "INSERT INTO migrations (filename) VALUES ($1) ON CONFLICT DO NOTHING",
                filename,
            )
            print(f"  Marked:     {filename}")
        print(f"\n{len(filenames)} migration(s) marked as applied.")
    finally:
        await conn.close()


async def mark_applied_pending():
    """Find pending migrations and mark them as applied (for bootstrap)."""
    conn = await get_connection()
    try:
        await ensure_migrations_table(conn)
        applied = await get_applied(conn)
        pending = [f.name for f in get_migration_files() if f.name not in applied]
        if not pending:
            print("No pending migrations to mark.")
            return
    finally:
        await conn.close()
    await mark_applied(pending)


async def unmark(filename: str):
    """Remove a migration from the tracking table so it can be re-run."""
    conn = await get_connection()
    try:
        await conn.execute("DELETE FROM migrations WHERE filename = $1", filename)
        print(f"  Unmarked:   {filename}")
    finally:
        await conn.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run local database migrations")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be applied")
    parser.add_argument("--mark-applied", action="store_true",
                        help="Mark all pending migrations as applied without running them")
    parser.add_argument("--unmark", metavar="FILENAME",
                        help="Remove a migration from tracking so it can be re-run")
    args = parser.parse_args()

    if not all([DB_USER, DB_PASSWORD, DB_NAME]):
        print("Error: DB_USER, DB_PASSWORD, and DB_NAME must be set in .env")
        sys.exit(1)

    if args.status:
        asyncio.run(show_status())
    elif args.mark_applied:
        asyncio.run(mark_applied_pending())
    elif args.unmark:
        asyncio.run(unmark(args.unmark))
    else:
        asyncio.run(run_migrations(dry_run=args.dry_run))


if __name__ == "__main__":
    main()