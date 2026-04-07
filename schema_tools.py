"""
Agentic tools for CRUD operations on a database schema YAML file.

Each tool is a simple function that can be called by an LLM to manage
tables and fields in a schema definition.
"""

import os
import yaml
from pathlib import Path
from typing import Optional


# Configuration - can be overridden via environment variables
SCHEMA_FILE = Path(os.getenv("SCHEMA_FILE", "schema/database.yaml"))


def _load_schema() -> dict:
    """Load the schema YAML file."""
    if not SCHEMA_FILE.exists():
        return {"tables": {}}
    with open(SCHEMA_FILE, "r") as f:
        data = yaml.safe_load(f)
        return data if data else {"tables": {}}


def _save_schema(data: dict) -> None:
    """Save the schema to YAML file."""
    SCHEMA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEMA_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


# =============================================================================
# TABLE CRUD
# =============================================================================


def create_table(name: str, description: Optional[str] = None) -> dict:
    """
    Create a new table in the schema.

    Args:
        name: Table name
        description: Optional table description

    Returns:
        Result dict with success status and message
    """
    schema = _load_schema()

    if name in schema["tables"]:
        return {"success": False, "message": f"Table '{name}' already exists"}

    schema["tables"][name] = {
        "description": description,
        "fields": {}
    }
    _save_schema(schema)

    return {"success": True, "message": f"Table '{name}' created"}


def read_table(name: str) -> dict:
    """
    Read a table definition from the schema.

    Args:
        name: Table name

    Returns:
        Result dict with success status and table data or error message
    """
    schema = _load_schema()

    if name not in schema["tables"]:
        return {"success": False, "message": f"Table '{name}' not found"}

    return {"success": True, "data": schema["tables"][name]}


def update_table(name: str, new_name: Optional[str] = None,
                 description: Optional[str] = None) -> dict:
    """
    Update a table definition.

    Args:
        name: Current table name
        new_name: New table name (optional)
        description: New description (optional)

    Returns:
        Result dict with success status and message
    """
    schema = _load_schema()

    if name not in schema["tables"]:
        return {"success": False, "message": f"Table '{name}' not found"}

    if new_name and new_name != name:
        if new_name in schema["tables"]:
            return {"success": False, "message": f"Table '{new_name}' already exists"}
        schema["tables"][new_name] = schema["tables"].pop(name)
        name = new_name

    if description is not None:
        schema["tables"][name]["description"] = description

    _save_schema(schema)

    return {"success": True, "message": f"Table '{name}' updated"}


def delete_table(name: str) -> dict:
    """
    Delete a table from the schema.

    Args:
        name: Table name

    Returns:
        Result dict with success status and message
    """
    schema = _load_schema()

    if name not in schema["tables"]:
        return {"success": False, "message": f"Table '{name}' not found"}

    del schema["tables"][name]
    _save_schema(schema)

    return {"success": True, "message": f"Table '{name}' deleted"}


def list_tables() -> dict:
    """
    List all tables in the schema.

    Returns:
        Result dict with success status and list of table names
    """
    schema = _load_schema()
    return {"success": True, "data": list(schema["tables"].keys())}


# =============================================================================
# FIELD CRUD
# =============================================================================


def create_field(table: str, name: str, type: str,
                  nullable: bool = True,
                  primary_key: bool = False,
                  unique: bool = False,
                  default: Optional[str] = None,
                  length: Optional[int] = None,
                  foreign_key: Optional[str] = None,
                  description: Optional[str] = None) -> dict:
    """
    Add a field to a table.

    Args:
        table: Table name
        name: Field name
        type: Field type (varchar, integer, serial, timestamp, etc.)
        nullable: Whether the field can be null (default True)
        primary_key: Whether this is a primary key (default False)
        unique: Whether this field must be unique (default False)
        default: Default value for the field
        length: Length for varchar fields
        foreign_key: Foreign key reference as "table.field"
        description: Field description

    Returns:
        Result dict with success status and message
    """
    schema = _load_schema()

    if table not in schema["tables"]:
        return {"success": False, "message": f"Table '{table}' not found"}

    if name in schema["tables"][table]["fields"]:
        return {"success": False, "message": f"Field '{name}' already exists in table '{table}'"}

    field_def = {"type": type}

    if nullable is not True:
        field_def["nullable"] = nullable
    if primary_key:
        field_def["primary_key"] = True
    if unique:
        field_def["unique"] = True
    if default is not None:
        field_def["default"] = default
    if length is not None:
        field_def["length"] = length
    if foreign_key is not None:
        field_def["foreign_key"] = foreign_key
    if description is not None:
        field_def["description"] = description

    schema["tables"][table]["fields"][name] = field_def
    _save_schema(schema)

    return {"success": True, "message": f"Field '{name}' added to table '{table}'"}


def read_field(table: str, name: str) -> dict:
    """
    Read a field definition from a table.

    Args:
        table: Table name
        name: Field name

    Returns:
        Result dict with success status and field data or error message
    """
    schema = _load_schema()

    if table not in schema["tables"]:
        return {"success": False, "message": f"Table '{table}' not found"}

    if name not in schema["tables"][table]["fields"]:
        return {"success": False, "message": f"Field '{name}' not found in table '{table}'"}

    return {"success": True, "data": schema["tables"][table]["fields"][name]}


def update_field(table: str, name: str, **updates) -> dict:
    """
    Update a field definition.

    Args:
        table: Table name
        name: Field name
        **updates: Field properties to update (type, nullable, unique, etc.)

    Returns:
        Result dict with success status and message
    """
    schema = _load_schema()

    if table not in schema["tables"]:
        return {"success": False, "message": f"Table '{table}' not found"}

    if name not in schema["tables"][table]["fields"]:
        return {"success": False, "message": f"Field '{name}' not found in table '{table}'"}

    field = schema["tables"][table]["fields"][name]

    # Handle rename
    new_name = updates.pop("new_name", None)
    if new_name and new_name != name:
        if new_name in schema["tables"][table]["fields"]:
            return {"success": False, "message": f"Field '{new_name}' already exists in table '{table}'"}
        schema["tables"][table]["fields"][new_name] = field
        del schema["tables"][table]["fields"][name]
        name = new_name

    # Apply other updates
    for key, value in updates.items():
        if value is None:
            field.pop(key, None)
        else:
            field[key] = value

    _save_schema(schema)

    return {"success": True, "message": f"Field '{name}' updated in table '{table}'"}


def delete_field(table: str, name: str) -> dict:
    """
    Delete a field from a table.

    Args:
        table: Table name
        name: Field name

    Returns:
        Result dict with success status and message
    """
    schema = _load_schema()

    if table not in schema["tables"]:
        return {"success": False, "message": f"Table '{table}' not found"}

    if name not in schema["tables"][table]["fields"]:
        return {"success": False, "message": f"Field '{name}' not found in table '{table}'"}

    del schema["tables"][table]["fields"][name]
    _save_schema(schema)

    return {"success": True, "message": f"Field '{name}' deleted from table '{table}'"}


def list_fields(table: str) -> dict:
    """
    List all fields in a table.

    Args:
        table: Table name

    Returns:
        Result dict with success status and list of field names
    """
    schema = _load_schema()

    if table not in schema["tables"]:
        return {"success": False, "message": f"Table '{table}' not found"}

    return {"success": True, "data": list(schema["tables"][table]["fields"].keys())}


def create_uuid_primary_key(table: str, name: str = "id",
                             description: Optional[str] = None) -> dict:
    """
    Add a UUID primary key field to a table with auto-generated random values.

    This is a convenience function that creates a field with:
    - type: uuid
    - primary_key: true
    - nullable: false
    - default: gen_random_uuid() (PostgreSQL function for random UUIDs)

    Args:
        table: Table name
        name: Field name (default: "id")
        description: Optional field description

    Returns:
        Result dict with success status and message
    """
    return create_field(
        table=table,
        name=name,
        type="uuid",
        nullable=False,
        primary_key=True,
        default="gen_random_uuid()",
        description=description
    )


# =============================================================================
# TOOL REGISTRY (for LLM use)
# =============================================================================


TOOLS = [
    {"name": "create_table", "function": create_table,
     "description": "Create a new table in the database schema"},
    {"name": "read_table", "function": read_table,
     "description": "Read a table definition from the schema"},
    {"name": "update_table", "function": update_table,
     "description": "Update a table name or description"},
    {"name": "delete_table", "function": delete_table,
     "description": "Delete a table from the schema"},
    {"name": "list_tables", "function": list_tables,
     "description": "List all tables in the schema"},
    {"name": "create_field", "function": create_field,
     "description": "Add a field to a table"},
    {"name": "read_field", "function": read_field,
     "description": "Read a field definition from a table"},
    {"name": "update_field", "function": update_field,
     "description": "Update a field definition"},
    {"name": "delete_field", "function": delete_field,
     "description": "Delete a field from a table"},
    {"name": "list_fields", "function": list_fields,
     "description": "List all fields in a table"},
    {"name": "create_uuid_primary_key", "function": create_uuid_primary_key,
     "description": "Add a UUID primary key field with auto-generated random values"},
]


def get_tool(name: str) -> Optional[dict]:
    """Get a tool by name."""
    for tool in TOOLS:
        if tool["name"] == name:
            return tool
    return None