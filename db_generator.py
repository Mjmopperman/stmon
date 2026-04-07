"""
Database SQL migration generator from YAML schema definitions.

Reads schema/database.yaml and generates a PostgreSQL migration file
in db/migrations/ with the next sequence number.

Usage:
    python db_generator.py                  # Auto-numbered output in db/migrations/
    python db_generator.py -o my_file.sql   # Custom output path
    python db_generator.py --dry-run        # Print SQL without writing
"""

import os
import re
import yaml
from pathlib import Path
from typing import Optional


# Configuration
SCHEMA_FILE = Path(os.getenv("SCHEMA_FILE", "schema/database.yaml"))
MIGRATIONS_DIR = Path(os.getenv("MIGRATIONS_DIR", "db/migrations"))

# Type mapping: YAML types → PostgreSQL types
YAML_TO_PG_TYPE = {
    "serial": "SERIAL",
    "integer": "INTEGER",
    "int": "INTEGER",
    "bigint": "BIGINT",
    "smallint": "SMALLINT",
    "varchar": "VARCHAR",
    "char": "CHAR",
    "text": "TEXT",
    "boolean": "BOOLEAN",
    "bool": "BOOLEAN",
    "decimal": "DECIMAL",
    "numeric": "NUMERIC",
    "float": "REAL",
    "double": "DOUBLE PRECISION",
    "timestamp": "TIMESTAMPTZ",
    "timestamptz": "TIMESTAMPTZ",
    "date": "DATE",
    "time": "TIME",
    "uuid": "UUID",
    "json": "JSON",
    "jsonb": "JSONB",
}


def load_schema() -> dict:
    """Load the database YAML file."""
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")
    with open(SCHEMA_FILE, "r") as f:
        data = yaml.safe_load(f)
    return data if data else {"tables": {}}


def pg_type(yaml_type: str, length: Optional[int] = None) -> str:
    """Convert YAML type to PostgreSQL type string."""
    base = YAML_TO_PG_TYPE.get(yaml_type.lower(), yaml_type.upper())
    if base == "VARCHAR" and length:
        return f"VARCHAR({length})"
    if base == "CHAR" and length:
        return f"CHAR({length})"
    if base == "DECIMAL" and length:
        return f"DECIMAL({length})"
    return base


def pg_default(default_value) -> str:
    """Format a default value for PostgreSQL."""
    if isinstance(default_value, bool):
        return "TRUE" if default_value else "FALSE"
    if default_value == "now()" or default_value == "CURRENT_TIMESTAMP":
        return "now()"
    if isinstance(default_value, str):
        if default_value.startswith("gen_random_uuid()"):
            return "gen_random_uuid()"
        if default_value.lower() in ("true", "false"):
            return default_value.upper()
        # Numeric defaults
        try:
            float(default_value)
            return str(default_value)
        except (ValueError, TypeError):
            pass
        # String default
        return f"'{default_value}'"
    return str(default_value)


def generate_table(table_name: str, table_def: dict) -> str:
    """Generate CREATE TABLE SQL for a single table."""
    fields = table_def.get("fields", {})
    description = table_def.get("description")

    lines = []
    if description:
        lines.append(f"-- {description}")
    lines.append(f"CREATE TABLE IF NOT EXISTS {table_name} (")

    col_lines = []
    constraints = []
    fk_constraints = []
    indexes = []

    for field_name, field_attrs in fields.items():
        # Simple format: field: type_string
        if isinstance(field_attrs, str):
            col_type = pg_type(field_attrs)
            col_lines.append(f"    {field_name} {col_type}")
            continue

        # Full format: field: {type, ...}
        yaml_type = field_attrs.get("type", "text")
        length = field_attrs.get("length")
        nullable = field_attrs.get("nullable", True)
        primary_key = field_attrs.get("primary_key", False)
        unique = field_attrs.get("unique", False)
        default = field_attrs.get("default")
        foreign_key = field_attrs.get("foreign_key")

        col_type = pg_type(yaml_type, length)
        parts = [f"    {field_name}", col_type]

        if not nullable:
            parts.append("NOT NULL")

        if primary_key:
            parts.append("PRIMARY KEY")

        if unique and not primary_key:
            parts.append("UNIQUE")

        if default is not None:
            parts.append(f"DEFAULT {pg_default(default)}")

        col_lines.append(" ".join(parts))

        # Collect foreign key constraints
        if foreign_key:
            ref_table, ref_col = foreign_key.split(".")
            fk_constraints.append(
                f"    FOREIGN KEY ({field_name}) REFERENCES {ref_table}({ref_col}) ON DELETE CASCADE"
            )
            indexes.append((table_name, field_name))

    # Combine column definitions and constraints
    all_lines = col_lines + fk_constraints
    lines.append(",\n".join(all_lines))
    lines.append(");")

    # Generate indexes for foreign key columns
    for tbl, col in indexes:
        idx_name = f"idx_{tbl}_{col}"
        lines.append(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl}({col});")

    return "\n".join(lines)


def next_migration_number() -> str:
    """Determine the next migration sequence number."""
    if not MIGRATIONS_DIR.exists():
        return "001"

    existing = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not existing:
        return "001"

    # Extract numbers from filenames like 001_init.sql
    numbers = []
    for f in existing:
        match = re.match(r"(\d+)", f.name)
        if match:
            numbers.append(int(match.group(1)))

    next_num = max(numbers) + 1 if numbers else 1
    return f"{next_num:03d}"


def scan_existing_tables() -> set:
    """Scan all existing migration SQL files for CREATE TABLE names."""
    tables = set()
    if not MIGRATIONS_DIR.exists():
        return tables
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        with open(sql_file, "r") as f:
            for match in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?(\w+)", f.read(), re.IGNORECASE):
                tables.add(match.group(1).lower())
    return tables


def generate_migration(schema: dict, exclude: Optional[set] = None) -> str:
    """Generate the full SQL migration from schema."""
    tables = schema.get("tables", {})
    exclude = exclude or set()

    if not tables:
        return "-- Empty migration: no tables defined in schema\n"

    included = {k: v for k, v in tables.items() if k.lower() not in exclude}
    if not included:
        return "-- No new tables to create\n"

    lines = [
        "-- Auto-generated database migration from schema/database.yaml",
        f"-- Tables: {', '.join(included.keys())}",
        "",
    ]

    for table_name, table_def in included.items():
        lines.append(generate_table(table_name, table_def))
        lines.append("")

    return "\n".join(lines)


def main():
    """Generate the SQL migration file."""
    import argparse
    parser = argparse.ArgumentParser(description="Generate SQL migration from database.yaml")
    parser.add_argument("--output", "-o", help="Output file path (default: auto-numbered in db/migrations/)")
    parser.add_argument("--dry-run", action="store_true", help="Print SQL without writing")
    parser.add_argument("--additive", action="store_true",
                        help="Only include tables not already created in existing migration files")
    args = parser.parse_args()

    print(f"Loading schema from: {SCHEMA_FILE}")
    schema = load_schema()

    tables = schema.get("tables", {})
    print(f"Found {len(tables)} table(s): {', '.join(tables.keys())}")

    exclude = set()
    if args.additive:
        exclude = scan_existing_tables()
        if exclude:
            print(f"Skipping existing tables: {', '.join(sorted(exclude))}")

    sql = generate_migration(schema, exclude=exclude)

    if args.dry_run:
        print("\n" + sql)
        return

    if args.output:
        output_path = Path(args.output)
    else:
        seq = next_migration_number()
        output_path = MIGRATIONS_DIR / f"{seq}_from_yaml.sql"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(sql)

    print(f"Generated migration: {output_path}")


if __name__ == "__main__":
    main()