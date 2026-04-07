"""
Code generator for FastAPI routers from YAML endpoint definitions.

Reads schema/endpoints.yaml and generates:
1. Pydantic models for request/response
2. FastAPI router with endpoints using Hasura GraphQL

Usage:
    python generator.py                  # Generate to app/routers/generated.py
    python generator.py --output path.py  # Generate to custom path
"""

import os
import yaml
from pathlib import Path
from typing import Optional


# Configuration
ENDPOINTS_FILE = Path(os.getenv("ENDPOINTS_FILE", "schema/endpoints.yaml"))
OUTPUT_FILE = Path(os.getenv("OUTPUT_FILE", "app/routers/generated.py"))


# Type mapping: YAML types → Python/Pydantic types
YAML_TO_PYTHON_TYPE = {
    "int": "int",
    "integer": "int",
    "str": "str",
    "string": "str",
    "varchar": "str",
    "text": "str",
    "bool": "bool",
    "boolean": "bool",
    "float": "float",
    "decimal": "float",
    "datetime": "datetime",
    "timestamp": "datetime",
    "uuid": "UUID",
}


def load_endpoints() -> dict:
    """Load the endpoints YAML file."""
    if not ENDPOINTS_FILE.exists():
        raise FileNotFoundError(f"Endpoints file not found: {ENDPOINTS_FILE}")
    with open(ENDPOINTS_FILE, "r") as f:
        data = yaml.safe_load(f)
        return data if data else {"endpoints": {}, "models": {}}


def python_type(yaml_type: str, required: bool = True) -> str:
    """Convert YAML type to Python type annotation."""
    base = YAML_TO_PYTHON_TYPE.get(yaml_type.lower(), "str")
    if not required:
        return f"Optional[{base}]"
    return base


def generate_imports() -> str:
    """Generate the imports section."""
    return '''"""
Auto-generated FastAPI router from endpoints.yaml.
DO NOT EDIT - regenerate with: python generator.py
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.hasura import hasura_client

router = APIRouter()
'''


def generate_model(name: str, model_def: dict) -> str:
    """Generate a Pydantic model class."""
    fields = model_def.get("fields", {})
    description = model_def.get("description", "")

    lines = [f"\nclass {name}(BaseModel):"]

    if description:
        lines.append(f'    """{description}"""')

    for field_name, field_attrs in fields.items():
        if isinstance(field_attrs, str):
            # Simple format: field: type
            py_type = python_type(field_attrs, required=True)
            lines.append(f"    {field_name}: {py_type}")
        else:
            # Full format: field: {type, required, ...}
            field_type = field_attrs.get("type", "str")
            required = field_attrs.get("required", True)
            py_type = python_type(field_type, required)
            lines.append(f"    {field_name}: {py_type}")

    return "\n".join(lines)


def generate_endpoint(name: str, endpoint_def: dict, models: dict) -> str:
    """Generate a FastAPI endpoint function."""
    path = endpoint_def.get("path", f"/{name}")
    method = endpoint_def.get("method", "GET").lower()
    description = endpoint_def.get("description", "")
    request_model = endpoint_def.get("request")
    response_model = endpoint_def.get("response")
    graphql_query = endpoint_def.get("graphql_query")
    graphql_type = endpoint_def.get("graphql_type", "query")

    # Build function signature
    func_name = name.replace("-", "_")

    # Extract path parameters
    path_params = []
    import re
    for match in re.finditer(r'\{(\w+)\}', path):
        path_params.append(match.group(1))

    # Build parameters
    params = []
    for param in path_params:
        # Determine param type from models if available
        params.append(f"{param}: str")  # Default to str, could be int/UUID

    # Add request body for POST/PUT/PATCH
    body_param = ""
    if request_model and method in ("post", "put", "patch"):
        body_param = f"{request_model.lower()}: {request_model}"

    # Build decorator
    decorator = f"@router.{method}(\"{path}\""
    if response_model:
        # Handle array notation: Model[]
        if response_model.endswith("[]"):
            resp = response_model[:-2]
            decorator += f", response_model=List[{resp}]"
        else:
            decorator += f", response_model={response_model}"
    if method == "post":
        decorator += ", status_code=201"
    decorator += ")"

    # Build function
    lines = [f"\n\n{decorator}"]

    # Function signature
    sig_parts = [f"async def {func_name}("]
    all_params = params[:]
    if body_param:
        all_params.append(body_param)
    sig_parts.append(", ".join(all_params))
    sig_parts.append("):")
    lines.append("".join(sig_parts))

    # Docstring
    if description:
        lines.append(f'    """{description}"""')

    # Function body
    if graphql_query:
        lines.extend(generate_graphql_body(name, graphql_query, graphql_type, path_params, body_param, request_model))
    else:
        lines.extend(generate_placeholder_body(name, path_params))

    return "\n".join(lines)


def generate_graphql_body(
    name: str,
    query: str,
    query_type: str,
    path_params: list,
    body_param: str,
    request_model: Optional[str]
) -> list:
    """Generate the function body for a GraphQL endpoint."""
    lines = []

    # Build variables dict
    var_parts = []
    for param in path_params:
        # Try to convert to int if it looks numeric
        var_parts.append(f'"{param}": {param}')

    if body_param and request_model:
        lines.append(f"    # Build variables from request model")
        lines.append(f"    data = {request_model.lower()}.model_dump(exclude_none=True)")
        for param in path_params:
            var_parts.append(f'"{param}": {param}')

    # Execute GraphQL query
    if var_parts:
        lines.append(f'    variables = {{{", ".join(var_parts)}}}' if var_parts else '    variables = {}')
        if body_param and request_model:
            lines.append("    variables.update(data)")
        lines.append(f'    result = await hasura_client.query("""')
    else:
        lines.append(f'    result = await hasura_client.query("""')

    # Indent the query
    for line in query.strip().split("\n"):
        lines.append(f"        {line}")
    lines.append('    """' + (', variables=variables)' if var_parts else ')'))

    # Extract data from result
    entity_name = name.split("_")[0]  # e.g., "user_list" -> "user"
    lines.append(f'    items = result.get("data", {{}}).get("{entity_name}", [])')

    # Return
    if path_params and not body_param:
        # Single item lookup
        lines.append("    if not items:")
        lines.append(f'        raise HTTPException(status_code=404, detail="{entity_name.capitalize()} not found")')
        lines.append("    return items[0]")
    else:
        lines.append("    return items")

    return lines


def generate_placeholder_body(name: str, path_params: list) -> list:
    """Generate a placeholder body for endpoints without GraphQL."""
    lines = []
    lines.append(f'    # TODO: Implement endpoint logic')
    lines.append(f'    return {{"message": "Endpoint {name} not implemented"}}')
    return lines


def generate_router(endpoints_data: dict) -> str:
    """Generate the complete router file."""
    models = endpoints_data.get("models", {})
    endpoints = endpoints_data.get("endpoints", {})

    # Start with imports
    output = [generate_imports()]

    # Generate models
    output.append("\n\n# =============================================================================")
    output.append("# Pydantic Models")
    output.append("# =============================================================================")

    for model_name, model_def in models.items():
        output.append(generate_model(model_name, model_def))

    # Generate endpoints
    output.append("\n\n# =============================================================================")
    output.append("# Endpoints")
    output.append("# =============================================================================")

    for endpoint_name, endpoint_def in endpoints.items():
        output.append(generate_endpoint(endpoint_name, endpoint_def, models))

    return "\n".join(output)


def main():
    """Generate the router file."""
    print(f"Loading endpoints from: {ENDPOINTS_FILE}")
    endpoints_data = load_endpoints()

    print(f"Found {len(endpoints_data.get('models', {}))} models")
    print(f"Found {len(endpoints_data.get('endpoints', {}))} endpoints")

    router_code = generate_router(endpoints_data)

    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        f.write(router_code)

    print(f"Generated router: {OUTPUT_FILE}")
    return OUTPUT_FILE


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate FastAPI router from endpoints.yaml")
    parser.add_argument("--output", "-o", help="Output file path", default=str(OUTPUT_FILE))
    args = parser.parse_args()

    OUTPUT_FILE = Path(args.output)
    main()