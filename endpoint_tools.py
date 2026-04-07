"""
Agentic tools for CRUD operations on endpoint definitions.

Each tool is a simple function that can be called by an LLM to manage
FastAPI endpoint definitions in a YAML file.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, List


# Configuration - can be overridden via environment variables
ENDPOINTS_FILE = Path(os.getenv("ENDPOINTS_FILE", "schema/endpoints.yaml"))

# Valid HTTP methods
VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _load_endpoints() -> dict:
    """Load the endpoints YAML file."""
    if not ENDPOINTS_FILE.exists():
        return {"endpoints": {}}
    with open(ENDPOINTS_FILE, "r") as f:
        data = yaml.safe_load(f)
        return data if data else {"endpoints": {}}


def _save_endpoints(data: dict) -> None:
    """Save the endpoints to YAML file."""
    ENDPOINTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ENDPOINTS_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


# =============================================================================
# ENDPOINT CRUD
# =============================================================================


def create_endpoint(
    name: str,
    path: str,
    method: str,
    description: Optional[str] = None,
    request: Optional[str] = None,
    response: Optional[str] = None,
    tags: Optional[List[str]] = None,
    auth_required: bool = False,
    graphql_query: Optional[str] = None,
    graphql_type: Optional[str] = None,
) -> dict:
    """
    Create a new endpoint definition.

    Args:
        name: Endpoint identifier (used as function name)
        path: URL path (e.g., "/users/{user_id}")
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        description: Endpoint description
        request: Request model name (Pydantic model)
        response: Response model name (Pydantic model)
        tags: List of tags for grouping in OpenAPI docs
        auth_required: Whether authentication is required
        graphql_query: GraphQL query/mutation string (for Hasura-backed endpoints)
        graphql_type: "query" or "mutation" (required if graphql_query is set)

    Returns:
        Result dict with success status and message
    """
    method = method.upper()
    if method not in VALID_METHODS:
        return {
            "success": False,
            "message": f"Invalid method '{method}'. Must be one of: {', '.join(sorted(VALID_METHODS))}"
        }

    if graphql_query and graphql_type not in ("query", "mutation"):
        return {
            "success": False,
            "message": f"graphql_type must be 'query' or 'mutation' when graphql_query is provided"
        }

    endpoints = _load_endpoints()

    if name in endpoints["endpoints"]:
        return {"success": False, "message": f"Endpoint '{name}' already exists"}

    endpoint_def = {
        "path": path,
        "method": method,
    }

    if description is not None:
        endpoint_def["description"] = description
    if request is not None:
        endpoint_def["request"] = request
    if response is not None:
        endpoint_def["response"] = response
    if tags:
        endpoint_def["tags"] = tags
    if auth_required:
        endpoint_def["auth_required"] = True
    if graphql_query:
        endpoint_def["graphql_query"] = graphql_query
        endpoint_def["graphql_type"] = graphql_type

    endpoints["endpoints"][name] = endpoint_def
    _save_endpoints(endpoints)

    return {"success": True, "message": f"Endpoint '{name}' created ({method} {path})"}


def read_endpoint(name: str) -> dict:
    """
    Read an endpoint definition.

    Args:
        name: Endpoint identifier

    Returns:
        Result dict with success status and endpoint data or error message
    """
    endpoints = _load_endpoints()

    if name not in endpoints["endpoints"]:
        return {"success": False, "message": f"Endpoint '{name}' not found"}

    return {"success": True, "data": endpoints["endpoints"][name]}


def update_endpoint(
    name: str,
    new_name: Optional[str] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
    description: Optional[str] = None,
    request: Optional[str] = None,
    response: Optional[str] = None,
    tags: Optional[List[str]] = None,
    auth_required: Optional[bool] = None,
    graphql_query: Optional[str] = None,
    graphql_type: Optional[str] = None,
) -> dict:
    """
    Update an endpoint definition.

    Args:
        name: Current endpoint identifier
        new_name: New endpoint identifier (optional)
        path: New URL path (optional)
        method: New HTTP method (optional)
        description: New description (optional)
        request: New request model name (optional)
        response: New response model name (optional)
        tags: New tags list (optional)
        auth_required: New auth requirement (optional)
        graphql_query: GraphQL query/mutation string (optional)
        graphql_type: "query" or "mutation" (optional)

    Returns:
        Result dict with success status and message
    """
    endpoints = _load_endpoints()

    if name not in endpoints["endpoints"]:
        return {"success": False, "message": f"Endpoint '{name}' not found"}

    endpoint = endpoints["endpoints"][name]

    # Handle rename
    if new_name and new_name != name:
        if new_name in endpoints["endpoints"]:
            return {"success": False, "message": f"Endpoint '{new_name}' already exists"}
        endpoints["endpoints"][new_name] = endpoint
        del endpoints["endpoints"][name]
        name = new_name

    if method is not None:
        method = method.upper()
        if method not in VALID_METHODS:
            return {
                "success": False,
                "message": f"Invalid method '{method}'. Must be one of: {', '.join(sorted(VALID_METHODS))}"
            }
        endpoint["method"] = method

    if path is not None:
        endpoint["path"] = path

    # Update or clear optional fields
    for field, value in [
        ("description", description),
        ("request", request),
        ("response", response),
        ("tags", tags),
    ]:
        if value is not None:
            endpoint[field] = value

    if auth_required is not None:
        endpoint["auth_required"] = auth_required

    if graphql_query is not None:
        if graphql_type not in ("query", "mutation"):
            return {"success": False, "message": "graphql_type must be 'query' or 'mutation'"}
        endpoint["graphql_query"] = graphql_query
        endpoint["graphql_type"] = graphql_type

    _save_endpoints(endpoints)
    return {"success": True, "message": f"Endpoint '{name}' updated"}


def delete_endpoint(name: str) -> dict:
    """
    Delete an endpoint definition.

    Args:
        name: Endpoint identifier

    Returns:
        Result dict with success status and message
    """
    endpoints = _load_endpoints()

    if name not in endpoints["endpoints"]:
        return {"success": False, "message": f"Endpoint '{name}' not found"}

    del endpoints["endpoints"][name]
    _save_endpoints(endpoints)

    return {"success": True, "message": f"Endpoint '{name}' deleted"}


def list_endpoints() -> dict:
    """
    List all endpoint names.

    Returns:
        Result dict with success status and list of endpoint names
    """
    endpoints = _load_endpoints()
    return {"success": True, "data": list(endpoints["endpoints"].keys())}


def list_endpoints_by_method(method: str) -> dict:
    """
    List all endpoints for a specific HTTP method.

    Args:
        method: HTTP method to filter by

    Returns:
        Result dict with success status and list of endpoint names
    """
    method = method.upper()
    endpoints = _load_endpoints()

    matching = [
        name for name, defn in endpoints["endpoints"].items()
        if defn.get("method") == method
    ]

    return {"success": True, "data": matching}


def list_endpoints_by_tag(tag: str) -> dict:
    """
    List all endpoints with a specific tag.

    Args:
        tag: Tag to filter by

    Returns:
        Result dict with success status and list of endpoint names
    """
    endpoints = _load_endpoints()

    matching = [
        name for name, defn in endpoints["endpoints"].items()
        if tag in defn.get("tags", [])
    ]

    return {"success": True, "data": matching}


# =============================================================================
# MODEL CRUD (for Pydantic request/response models)
# =============================================================================


def create_model(
    name: str,
    fields: dict,
    description: Optional[str] = None,
) -> dict:
    """
    Create a Pydantic model definition for request/response.

    Args:
        name: Model name (e.g., "UserCreate", "UserResponse")
        fields: Dict of field_name -> {type, required, default, description}
        description: Model description

    Returns:
        Result dict with success status and message
    """
    endpoints = _load_endpoints()

    # Initialize models section if not exists
    if "models" not in endpoints:
        endpoints["models"] = {}

    if name in endpoints["models"]:
        return {"success": False, "message": f"Model '{name}' already exists"}

    model_def = {"fields": fields}
    if description:
        model_def["description"] = description

    endpoints["models"][name] = model_def
    _save_endpoints(endpoints)

    return {"success": True, "message": f"Model '{name}' created"}


def read_model(name: str) -> dict:
    """
    Read a model definition.

    Args:
        name: Model name

    Returns:
        Result dict with success status and model data or error message
    """
    endpoints = _load_endpoints()

    if "models" not in endpoints or name not in endpoints["models"]:
        return {"success": False, "message": f"Model '{name}' not found"}

    return {"success": True, "data": endpoints["models"][name]}


def update_model(
    name: str,
    new_name: Optional[str] = None,
    fields: Optional[dict] = None,
    description: Optional[str] = None,
) -> dict:
    """
    Update a model definition.

    Args:
        name: Current model name
        new_name: New model name (optional)
        fields: New fields dict (optional, replaces all fields)
        description: New description (optional)

    Returns:
        Result dict with success status and message
    """
    endpoints = _load_endpoints()

    if "models" not in endpoints or name not in endpoints["models"]:
        return {"success": False, "message": f"Model '{name}' not found"}

    model = endpoints["models"][name]

    # Handle rename
    if new_name and new_name != name:
        if new_name in endpoints["models"]:
            return {"success": False, "message": f"Model '{new_name}' already exists"}
        endpoints["models"][new_name] = model
        del endpoints["models"][name]
        name = new_name

    if fields is not None:
        model["fields"] = fields

    if description is not None:
        model["description"] = description

    _save_endpoints(endpoints)
    return {"success": True, "message": f"Model '{name}' updated"}


def delete_model(name: str) -> dict:
    """
    Delete a model definition.

    Args:
        name: Model name

    Returns:
        Result dict with success status and message
    """
    endpoints = _load_endpoints()

    if "models" not in endpoints or name not in endpoints["models"]:
        return {"success": False, "message": f"Model '{name}' not found"}

    del endpoints["models"][name]
    _save_endpoints(endpoints)

    return {"success": True, "message": f"Model '{name}' deleted"}


def list_models() -> dict:
    """
    List all model names.

    Returns:
        Result dict with success status and list of model names
    """
    endpoints = _load_endpoints()
    models = endpoints.get("models", {})
    return {"success": True, "data": list(models.keys())}


def add_model_field(
    model: str,
    name: str,
    type: str,
    required: bool = True,
    default: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """
    Add a field to a model.

    Args:
        model: Model name
        name: Field name
        type: Field type (str, int, bool, float, datetime, etc.)
        required: Whether the field is required (default True)
        default: Default value for optional fields
        description: Field description

    Returns:
        Result dict with success status and message
    """
    endpoints = _load_endpoints()

    if "models" not in endpoints or model not in endpoints["models"]:
        return {"success": False, "message": f"Model '{model}' not found"}

    fields = endpoints["models"][model]["fields"]

    if name in fields:
        return {"success": False, "message": f"Field '{name}' already exists in model '{model}'"}

    field_def = {"type": type, "required": required}
    if default is not None:
        field_def["default"] = default
    if description is not None:
        field_def["description"] = description

    fields[name] = field_def
    _save_endpoints(endpoints)

    return {"success": True, "message": f"Field '{name}' added to model '{model}'"}


# =============================================================================
# ENTITY CRUD (convenience function)
# =============================================================================


# Type mapping: database types -> Pydantic types
DB_TO_PYDANTIC_TYPE = {
    "serial": "int",
    "integer": "int",
    "uuid": "uuid",
    "varchar": "str",
    "text": "str",
    "timestamp": "datetime",
    "boolean": "bool",
    "decimal": "float",
    "float": "float",
}


def _load_database_schema() -> dict:
    """Load the database schema YAML file."""
    schema_file = Path(os.getenv("SCHEMA_FILE", "schema/database.yaml"))
    if not schema_file.exists():
        return {"tables": {}}
    with open(schema_file, "r") as f:
        data = yaml.safe_load(f)
        return data if data else {"tables": {}}


def create_entity_crud(
    table: str,
    tags: Optional[List[str]] = None,
    auth_required: bool = False,
) -> dict:
    """
    Create a full CRUD setup for an entity based on a database table.

    This creates:
    1. A Pydantic model based on the table's fields
    2. Five standard endpoints: _list, _get_id, _create, _update_id, _delete_id

    Args:
        table: Table name in database.yaml to base the entity on
        tags: Optional tags for grouping endpoints
        auth_required: Whether authentication is required for all endpoints

    Returns:
        Result dict with success status and details of what was created
    """
    # Load database schema
    db_schema = _load_database_schema()

    if table not in db_schema.get("tables", {}):
        return {"success": False, "message": f"Table '{table}' not found in database schema"}

    table_def = db_schema["tables"][table]
    fields_def = table_def.get("fields", {})

    if not fields_def:
        return {"success": False, "message": f"Table '{table}' has no fields defined"}

    # Convert database fields to Pydantic model fields
    model_fields = {}
    for field_name, field_attrs in fields_def.items():
        db_type = field_attrs.get("type", "varchar")
        pydantic_type = DB_TO_PYDANTIC_TYPE.get(db_type, "str")

        model_fields[field_name] = {
            "type": pydantic_type,
            "required": not field_attrs.get("nullable", True),
        }

    # Create model (capitalized entity name)
    model_name = table.capitalize()
    model_result = create_model(model_name, model_fields, description=f"{model_name} model based on {table} table")

    if not model_result.get("success"):
        return {"success": False, "message": f"Failed to create model: {model_result.get('message')}"}

    # Create endpoints
    endpoints_created = []
    endpoints_failed = []

    endpoint_defs = [
        ("list", "GET", f"/{table}/list", f"List all {table}", None, f"{model_name}[]"),
        ("get_id", "GET", f"/{table}/get/{{id}}", f"Get a single {table} by ID", None, model_name),
        ("create", "POST", f"/{table}/create", f"Create a new {table}", model_name, model_name),
        ("update_id", "POST", f"/{table}/update/{{id}}", f"Update a {table} by ID", model_name, model_name),
        ("delete_id", "DELETE", f"/{table}/delete/{{id}}", f"Delete a {table} by ID", None, None),
    ]

    for action, method, path, description, request, response in endpoint_defs:
        endpoint_name = f"{table}_{action}"
        result = create_endpoint(
            name=endpoint_name,
            path=path,
            method=method,
            description=description,
            request=request,
            response=response,
            tags=tags,
            auth_required=auth_required,
        )
        if result.get("success"):
            endpoints_created.append(endpoint_name)
        else:
            endpoints_failed.append(f"{endpoint_name}: {result.get('message')}")

    # Summary
    if endpoints_failed:
        return {
            "success": True,
            "message": f"Partially created entity CRUD for '{table}'",
            "model": model_name,
            "endpoints_created": endpoints_created,
            "endpoints_failed": endpoints_failed,
        }

    return {
        "success": True,
        "message": f"Created full CRUD for '{table}': model '{model_name}' and 5 endpoints",
        "model": model_name,
        "endpoints": endpoints_created,
    }


# =============================================================================
# GRAPHQL ENTITY CRUD
# =============================================================================


# Type mapping: Pydantic types -> GraphQL scalar types
PYDANTIC_TO_GRAPHQL_TYPE = {
    "int": "Int!",
    "uuid": "uuid!",
    "str": "String!",
    "datetime": "timestamptz!",
    "bool": "Boolean!",
    "float": "Float!",
}


def _get_graphql_type(pydantic_type: str, required: bool = True) -> str:
    """Convert Pydantic type to GraphQL type."""
    base_type = PYDANTIC_TO_GRAPHQL_TYPE.get(pydantic_type, "String!")
    if not required:
        base_type = base_type.rstrip("!")
    return base_type


def _build_graphql_fields(fields: dict) -> str:
    """Build GraphQL field selection string from model fields."""
    field_names = list(fields.keys())
    return "\n            ".join(field_names)


def _build_graphql_variables(fields: dict, include_id: bool = False) -> tuple:
    """Build GraphQL variable definitions and argument mapping.

    Returns:
        Tuple of (variable_defs, args_dict)
        variable_defs: str like "$id: Int!, $name: String!"
        args_dict: dict mapping variable names to field names for the mutation
    """
    vars_list = []
    args_dict = {}

    for field_name, field_attrs in fields.items():
        if not include_id and field_name == "id":
            continue
        pydantic_type = field_attrs.get("type", "str")
        required = field_attrs.get("required", False)
        gql_type = _get_graphql_type(pydantic_type, required)
        vars_list.append(f"${field_name}: {gql_type}")
        args_dict[field_name] = field_name

    return ", ".join(vars_list), args_dict


def create_graphql_crud(
    table: str,
    tags: Optional[List[str]] = None,
    auth_required: bool = False,
    id_type: str = "Int",
) -> dict:
    """
    Create a full CRUD setup for an entity using Hasura GraphQL.

    This creates:
    1. A Pydantic model based on the table's fields
    2. Five standard endpoints with GraphQL queries/mutations

    Args:
        table: Table name in database.yaml to base the entity on
        tags: Optional tags for grouping endpoints
        auth_required: Whether authentication is required for all endpoints
        id_type: GraphQL type for ID parameter ("Int" or "uuid")

    Returns:
        Result dict with success status and details of what was created
    """
    # Load database schema
    db_schema = _load_database_schema()

    if table not in db_schema.get("tables", {}):
        return {"success": False, "message": f"Table '{table}' not found in database schema"}

    table_def = db_schema["tables"][table]
    fields_def = table_def.get("fields", {})

    if not fields_def:
        return {"success": False, "message": f"Table '{table}' has no fields defined"}

    # Convert database fields to Pydantic model fields
    model_fields = {}
    for field_name, field_attrs in fields_def.items():
        db_type = field_attrs.get("type", "varchar")
        pydantic_type = DB_TO_PYDANTIC_TYPE.get(db_type, "str")

        model_fields[field_name] = {
            "type": pydantic_type,
            "required": not field_attrs.get("nullable", True),
        }

    # Create model (capitalized entity name)
    model_name = table.capitalize()
    model_result = create_model(model_name, model_fields, description=f"{model_name} model based on {table} table")

    if not model_result.get("success"):
        return {"success": False, "message": f"Failed to create model: {model_result.get('message')}"}

    # Build field selection for GraphQL
    field_selection = _build_graphql_fields(model_fields)

    # Determine ID field and type
    id_field = "id"
    for fn, fa in fields_def.items():
        if fa.get("primary_key"):
            id_field = fn
            if fa.get("type") == "uuid":
                id_type = "uuid"
            elif fa.get("type") in ("serial", "integer"):
                id_type = "Int"
            break

    # Determine which fields are creatable (excludes id, created_at, updated_at defaults)
    auto_fields = {"id", "created_at", "updated_at", "published_at"}
    create_fields = {k: v for k, v in model_fields.items() if k not in auto_fields}

    # Create endpoints with GraphQL queries
    endpoints_created = []
    endpoints_failed = []

    # 1. LIST endpoint
    list_query = f"""query {{
    {table} {{
        {field_selection}
    }}
}}"""
    result = create_endpoint(
        name=f"{table}_list",
        path=f"/{table}/list",
        method="GET",
        description=f"List all {table}",
        response=f"{model_name}[]",
        tags=tags,
        auth_required=auth_required,
        graphql_query=list_query,
        graphql_type="query",
    )
    if result.get("success"):
        endpoints_created.append(f"{table}_list")
    else:
        endpoints_failed.append(f"{table}_list: {result.get('message')}")

    # 2. GET BY ID endpoint
    get_query = f"""query Get{model_name}($id: {id_type}!) {{
    {table}(where: {{id: {{_eq: $id}}}}) {{
        {field_selection}
    }}
}}"""
    result = create_endpoint(
        name=f"{table}_get",
        path=f"/{table}/{{id}}",
        method="GET",
        description=f"Get a single {table} by ID",
        response=model_name,
        tags=tags,
        auth_required=auth_required,
        graphql_query=get_query,
        graphql_type="query",
    )
    if result.get("success"):
        endpoints_created.append(f"{table}_get")
    else:
        endpoints_failed.append(f"{table}_get: {result.get('message')}")

    # 3. CREATE endpoint
    var_defs, _ = _build_graphql_variables(create_fields)
    create_fields_str = ", ".join([f"{k}: ${k}" for k in create_fields.keys()])
    create_query = f"""mutation Create{model_name}({var_defs}) {{
    insert_{table}(objects: {{{create_fields_str}}}) {{
        returning {{
            {field_selection}
        }}
    }}
}}"""
    result = create_endpoint(
        name=f"{table}_create",
        path=f"/{table}",
        method="POST",
        description=f"Create a new {table}",
        request=model_name,
        response=model_name,
        tags=tags,
        auth_required=auth_required,
        graphql_query=create_query,
        graphql_type="mutation",
    )
    if result.get("success"):
        endpoints_created.append(f"{table}_create")
    else:
        endpoints_failed.append(f"{table}_create: {result.get('message')}")

    # 4. UPDATE endpoint
    update_query = f"""mutation Update{model_name}($id: {id_type}!, $changes: {table}_set_input!) {{
    update_{table}(where: {{id: {{_eq: $id}}}}, _set: $changes) {{
        returning {{
            {field_selection}
        }}
    }}
}}"""
    result = create_endpoint(
        name=f"{table}_update",
        path=f"/{table}/{{id}}",
        method="PUT",
        description=f"Update a {table} by ID",
        request=model_name,
        response=model_name,
        tags=tags,
        auth_required=auth_required,
        graphql_query=update_query,
        graphql_type="mutation",
    )
    if result.get("success"):
        endpoints_created.append(f"{table}_update")
    else:
        endpoints_failed.append(f"{table}_update: {result.get('message')}")

    # 5. DELETE endpoint
    delete_query = f"""mutation Delete{model_name}($id: {id_type}!) {{
    delete_{table}(where: {{id: {{_eq: $id}}}}) {{
        affected_rows
    }}
}}"""
    result = create_endpoint(
        name=f"{table}_delete",
        path=f"/{table}/{{id}}",
        method="DELETE",
        description=f"Delete a {table} by ID",
        tags=tags,
        auth_required=auth_required,
        graphql_query=delete_query,
        graphql_type="mutation",
    )
    if result.get("success"):
        endpoints_created.append(f"{table}_delete")
    else:
        endpoints_failed.append(f"{table}_delete: {result.get('message')}")

    # Summary
    if endpoints_failed:
        return {
            "success": True,
            "message": f"Partially created GraphQL CRUD for '{table}'",
            "model": model_name,
            "endpoints_created": endpoints_created,
            "endpoints_failed": endpoints_failed,
        }

    return {
        "success": True,
        "message": f"Created GraphQL CRUD for '{table}': model '{model_name}' and 5 endpoints",
        "model": model_name,
        "endpoints": endpoints_created,
    }


# =============================================================================
# SYNC ENDPOINTS WITH DATABASE TABLES
# =============================================================================


def sync_endpoints(
    tables: Optional[List[str]] = None,
    delete_orphans: bool = False,
    auth_required: bool = False,
    regenerate: bool = True,
) -> dict:
    """
    Sync endpoints.yaml with database.yaml and regenerate the router.

    For each table in database.yaml:
    - If no endpoints exist: create full GraphQL CRUD
    - If endpoints exist but missing GraphQL: recreate with GraphQL

    Optionally removes endpoints for tables that no longer exist.

    Args:
        tables: Specific tables to sync (default: all tables)
        delete_orphans: Delete endpoints for tables not in database.yaml
        auth_required: Whether authentication is required for all endpoints
        regenerate: Whether to run generator.py after sync (default: True)

    Returns:
        Result dict with success status and details of changes
    """
    # Load both files
    db_schema = _load_database_schema()
    endpoints_data = _load_endpoints()

    db_tables = set(db_schema.get("tables", {}).keys())

    if tables:
        # Filter to specified tables that exist
        tables_to_sync = set(tables) & db_tables
        missing_tables = set(tables) - db_tables
        if missing_tables:
            return {
                "success": False,
                "message": f"Tables not found in database.yaml: {', '.join(missing_tables)}"
            }
    else:
        tables_to_sync = db_tables

    results = {
        "created": [],
        "updated": [],
        "skipped": [],
        "deleted": [],
        "errors": []
    }

    # Standard endpoint names for a table
    def get_endpoint_names(table: str) -> List[str]:
        return [
            f"{table}_list",
            f"{table}_get",
            f"{table}_create",
            f"{table}_update",
            f"{table}_delete",
        ]

    # Check if endpoints have GraphQL queries
    def has_graphql(table: str) -> bool:
        for ep_name in get_endpoint_names(table):
            ep = endpoints_data.get("endpoints", {}).get(ep_name, {})
            if ep and "graphql_query" not in ep:
                return False
        return True

    # Sync each table
    for table in tables_to_sync:
        ep_names = get_endpoint_names(table)
        existing = [n for n in ep_names if n in endpoints_data.get("endpoints", {})]

        if not existing:
            # No endpoints: create new
            result = create_graphql_crud(table, auth_required=auth_required)
            if result.get("success"):
                results["created"].append(table)
            else:
                results["errors"].append(f"{table}: {result.get('message')}")
        elif not has_graphql(table):
            # Endpoints exist but missing GraphQL: recreate
            # Delete old endpoints and model
            for ep_name in ep_names:
                if ep_name in endpoints_data.get("endpoints", {}):
                    delete_endpoint(ep_name)

            model_name = table.capitalize()
            if model_name in endpoints_data.get("models", {}):
                delete_model(model_name)

            # Reload after deletions
            endpoints_data = _load_endpoints()

            # Create fresh with GraphQL
            result = create_graphql_crud(table, auth_required=auth_required)
            if result.get("success"):
                results["updated"].append(table)
            else:
                results["errors"].append(f"{table}: {result.get('message')}")
        else:
            # Already has GraphQL: skip
            results["skipped"].append(table)

    # Handle orphan endpoints
    if delete_orphans:
        all_ep_names = set(endpoints_data.get("endpoints", {}).keys())
        # Find endpoints that match {table}_{action} pattern
        for ep_name in list(all_ep_names):
            parts = ep_name.rsplit("_", 1)
            if len(parts) == 2:
                table_name, action = parts
                if action in ("list", "get", "create", "update", "delete"):
                    if table_name not in db_tables:
                        delete_endpoint(ep_name)
                        results["deleted"].append(ep_name)

    # Summary
    summary_parts = []
    if results["created"]:
        summary_parts.append(f"created {len(results['created'])} entities")
    if results["updated"]:
        summary_parts.append(f"updated {len(results['updated'])} entities")
    if results["skipped"]:
        summary_parts.append(f"skipped {len(results['skipped'])} entities (already synced)")
    if results["deleted"]:
        summary_parts.append(f"deleted {len(results['deleted'])} orphan endpoints")
    if results["errors"]:
        summary_parts.append(f"{len(results['errors'])} errors")

    if not summary_parts:
        summary = "No changes needed"
    else:
        summary = ", ".join(summary_parts)

    # Regenerate router if requested
    generated_file = None
    if regenerate:
        try:
            import subprocess
            result = subprocess.run(
                ["python", "generator.py"],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            if result.returncode == 0:
                generated_file = "app/routers/generated.py"
            else:
                results["errors"].append(f"Generator failed: {result.stderr}")
        except Exception as e:
            results["errors"].append(f"Generator error: {str(e)}")

    return {
        "success": len(results["errors"]) == 0,
        "message": f"Sync complete: {summary}",
        "results": results,
        "generated": generated_file
    }


# =============================================================================
# TOOL REGISTRY (for LLM use)
# =============================================================================


TOOLS = [
    # Endpoints
    {"name": "create_endpoint", "function": create_endpoint,
     "description": "Create a new FastAPI endpoint definition"},
    {"name": "read_endpoint", "function": read_endpoint,
     "description": "Read an endpoint definition"},
    {"name": "update_endpoint", "function": update_endpoint,
     "description": "Update an endpoint definition"},
    {"name": "delete_endpoint", "function": delete_endpoint,
     "description": "Delete an endpoint definition"},
    {"name": "list_endpoints", "function": list_endpoints,
     "description": "List all endpoint names"},
    {"name": "list_endpoints_by_method", "function": list_endpoints_by_method,
     "description": "List endpoints filtered by HTTP method"},
    {"name": "list_endpoints_by_tag", "function": list_endpoints_by_tag,
     "description": "List endpoints filtered by tag"},

    # Models
    {"name": "create_model", "function": create_model,
     "description": "Create a Pydantic model definition"},
    {"name": "read_model", "function": read_model,
     "description": "Read a model definition"},
    {"name": "update_model", "function": update_model,
     "description": "Update a model definition"},
    {"name": "delete_model", "function": delete_model,
     "description": "Delete a model definition"},
    {"name": "list_models", "function": list_models,
     "description": "List all model names"},
    {"name": "add_model_field", "function": add_model_field,
     "description": "Add a field to a Pydantic model"},

    # Entity CRUD (convenience)
    {"name": "create_entity_crud", "function": create_entity_crud,
     "description": "Create full CRUD setup (model + 5 endpoints) from a database table"},

    # GraphQL Entity CRUD
    {"name": "create_graphql_crud", "function": create_graphql_crud,
     "description": "Create full CRUD setup with GraphQL queries/mutations from a database table"},

    # Sync
    {"name": "sync_endpoints", "function": sync_endpoints,
     "description": "Sync endpoints.yaml with database.yaml - create missing endpoints, update stubs to include GraphQL"},
]


def get_tool(name: str) -> Optional[dict]:
    """Get a tool by name."""
    for tool in TOOLS:
        if tool["name"] == name:
            return tool
    return None