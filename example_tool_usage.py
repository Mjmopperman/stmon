"""
Ollama agent that uses schema tools to manage database schemas and endpoints.

Usage:
    python example_tool_usage.py                           # Interactive mode
    python example_tool_usage.py "your prompt here"       # Single prompt
    python example_tool_usage.py -f instructions.yaml     # Execute YAML instructions
    python example_tool_usage.py -f instructions.txt      # Execute text file (one prompt per line)

Text file format:
    - One natural language prompt per line
    - Lines starting with # are comments (ignored)
    - Empty lines are skipped

Set environment variables:
    OLLAMA_HOST       - Ollama server URL (default: http://localhost:11434)
    OLLAMA_API_KEY    - API key if using a hosted Ollama service (optional)
    OLLAMA_MODEL      - Model to use (default: qwen2.5-coder:7b)
    SCHEMA_FILE       - Path to schema YAML file (default: schema/database.yaml)
    ENDPOINTS_FILE    - Path to endpoints YAML file (default: schema/endpoints.yaml)
"""

import json
import os
import argparse
import inspect
import re
from typing import Optional
from pathlib import Path

import yaml
import ollama

import schema_tools
import endpoint_tools
import ui_tools


# Configuration
CONFIG = {
    "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "ollama_api_key": os.getenv("OLLAMA_API_KEY"),
    "ollama_model": os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"),
    "schema_file": Path(os.getenv("SCHEMA_FILE", "schema/database.yaml")),
    "endpoints_file": Path(os.getenv("ENDPOINTS_FILE", "schema/endpoints.yaml")),
    "ui_file": Path(os.getenv("UI_FILE", "schema/ui.yaml")),
}


def get_tool_definitions() -> list[dict]:
    """Get tool definitions in Ollama format."""
    definitions = []

    # Combine tools from all modules
    all_tools = schema_tools.TOOLS + endpoint_tools.TOOLS + ui_tools.TOOLS

    for tool in all_tools:
        fn = tool["function"]
        fn_name = tool["name"]

        # Build parameters schema from function signature
        sig = inspect.signature(fn)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            has_default = param.default != inspect.Parameter.empty

            # Map Python types to JSON schema types
            type_map = {
                str: "string",
                int: "integer",
                bool: "boolean",
                Optional[str]: "string",
                Optional[int]: "integer",
                Optional[bool]: "boolean",
            }
            json_type = type_map.get(param_type, "string")

            properties[param_name] = {"type": json_type}

            # Mark as required if no default
            if not has_default:
                required.append(param_name)

        definitions.append({
            "type": "function",
            "function": {
                "name": fn_name,
                "description": tool["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        })

    return definitions


def execute_tool_call(tool_name: str, arguments: dict) -> dict:
    """Execute a tool call by name with the given arguments."""
    # Search all modules for the tool
    tool = schema_tools.get_tool(tool_name) or endpoint_tools.get_tool(tool_name) or ui_tools.get_tool(tool_name)
    if not tool:
        return {"success": False, "message": f"Unknown tool: {tool_name}"}

    fn = tool["function"]

    # Check for missing required arguments
    sig = inspect.signature(fn)
    missing = []
    for param_name, param in sig.parameters.items():
        if param.default == inspect.Parameter.empty and param_name not in arguments:
            missing.append(param_name)

    if missing:
        return {"success": False, "message": f"Missing required arguments: {', '.join(missing)}"}

    return fn(**arguments)


def create_client() -> ollama.Client:
    """Create Ollama client with optional API key."""
    headers = {}
    if CONFIG["ollama_api_key"]:
        headers["Authorization"] = f"Bearer {CONFIG['ollama_api_key']}"

    return ollama.Client(host=CONFIG["ollama_host"], headers=headers if headers else None)


def extract_tool_calls(response: dict) -> list:
    """Extract tool calls from response, handling both native and text formats."""
    message = response.get("message", {})
    tool_calls = message.get("tool_calls", [])

    if tool_calls:
        return tool_calls

    # Fallback: parse JSON from content
    content = message.get("content", "")
    if not content:
        return []

    # Try to find JSON in the content
    json_pattern = r'\{[^{}]*"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^{}]*\}\s*\}'
    matches = re.findall(json_pattern, content, re.DOTALL)

    extracted = []
    for match in matches:
        try:
            data = json.loads(match)
            if "name" in data and "arguments" in data:
                extracted.append({
                    "function": {
                        "name": data["name"],
                        "arguments": data["arguments"]
                    }
                })
        except json.JSONDecodeError:
            continue

    # Also try parsing entire content as JSON
    if not extracted:
        try:
            data = json.loads(content.strip())
            if "name" in data and "arguments" in data:
                extracted.append({
                    "function": {
                        "name": data["name"],
                        "arguments": data["arguments"]
                    }
                })
        except json.JSONDecodeError:
            pass

    return extracted


def run_agent(user_message: str, max_iterations: int = 10) -> str:
    """
    Run the agent loop with Ollama.

    Args:
        user_message: The user's request
        max_iterations: Maximum tool call iterations to prevent infinite loops

    Returns:
        The final response from the agent
    """
    client = create_client()
    tools = get_tool_definitions()

    messages = [
        {
            "role": "system",
            "content": """You are a database schema, API endpoint, and UI page management assistant.
You have access to tools for managing tables, fields, FastAPI endpoints, and UI pages in YAML files.

## Workflow
1. First, understand what the user wants
2. Call the appropriate tools to make changes
3. Confirm what you've done after completing the task

## Available Tools

### Database Tables
- create_table(name, description?) - Create a new table
- read_table(name) - Get table definition
- update_table(name, new_name?, description?) - Update table
- delete_table(name) - Delete table
- list_tables() - List all tables

### Database Fields
- create_field(table, name, type, nullable?, primary_key?, unique?, default?, length?, foreign_key?, description?) - Add field
- read_field(table, name) - Get field definition
- update_field(table, name, **updates) - Update field (use new_name to rename)
- delete_field(table, name) - Delete field
- list_fields(table) - List all fields in a table
- create_uuid_primary_key(table, name="id", description?) - Add UUID primary key with auto-generated values

### API Endpoints
- create_endpoint(name, path, method, description?, request?, response?, tags?, auth_required?) - Create endpoint
- read_endpoint(name) - Get endpoint definition
- update_endpoint(name, new_name?, path?, method?, description?, request?, response?, tags?, auth_required?) - Update endpoint
- delete_endpoint(name) - Delete endpoint
- list_endpoints() - List all endpoints
- list_endpoints_by_method(method) - List endpoints by HTTP method (GET, POST, PUT, PATCH, DELETE)
- list_endpoints_by_tag(tag) - List endpoints by tag

### Pydantic Models
- create_model(name, fields, description?) - Create a Pydantic model
- read_model(name) - Get model definition
- update_model(name, new_name?, fields?, description?) - Update model
- delete_model(name) - Delete model
- list_models() - List all models
- add_model_field(model, name, type, required?, default?, description?) - Add field to model

### UI Pages
- create_page(name, title, description?, primary_actor?, use_case?, auth_required?, layout?) - Create a new page
- read_page(name) - Get page definition
- update_page(name, new_name?, title?, description?, primary_actor?, use_case?, auth_required?, layout?) - Update page
- delete_page(name) - Delete page
- list_pages() - List all pages
- list_pages_by_actor(actor) - List pages for a specific actor
- list_pages_by_use_case(use_case) - List pages for a specific use case

### UI Components
- add_component(page, component_type, component_id, title?, description?, endpoint?, model?, fields?, actions?, props?, position?) - Add component to page
- get_component(page, component_id) - Get component definition
- update_component(page, component_id, ...) - Update component
- remove_component(page, component_id) - Remove component from page
- list_components(page) - List all components in a page
- move_component(page, component_id, position) - Move component to new position

### Component Types
- form - Input form for creating/editing records
- detail - Read-only detail view
- table - Data table with search/pagination
- list - List view
- card - Card component
- modal - Modal dialog
- tabs - Tabbed interface
- wizard - Multi-step wizard
- chart - Chart/graph visualization
- map - Map component
- calendar - Calendar view
- upload - File upload component

### Convenience Functions
- create_entity_crud(table, tags?, auth_required?) - Create full CRUD setup from a database table
  - Creates a Pydantic model based on the table's fields
  - Creates 5 endpoints: {table}_list, {table}_get_id, {table}_create, {table}_update_id, {table}_delete_id
- create_page_from_endpoint(endpoint_name, page_name?, title?, description?, primary_actor?) - Create page from endpoint

## Field Types (Database)
- serial - auto-increment primary key
- uuid - UUID primary key (use create_uuid_primary_key for auto-generated)
- varchar - strings (specify length)
- integer - whole numbers
- decimal - prices/amounts
- boolean - true/false
- timestamp - dates/times

## Field Types (Pydantic Models)
- str - string
- int - integer
- bool - boolean
- float - float
- datetime - datetime

## IMPORTANT: Understanding "Entity" vs "Table"

An "entity" in this context means: a Pydantic model + CRUD endpoints for an EXISTING database table.

When user says "add X entity" or "create entity for X":
1. First check if the table exists using list_tables()
2. If table exists, call create_entity_crud("X") - use singular table name
3. If table does NOT exist, ask user if they want to create it first

DO NOT create a new table when asked to "add entity". Entities are derived from existing tables.

## Examples

User: "Create a users table with id and email"
You: Call create_table("users"), then create_uuid_primary_key("users"), then create_field("users", "email", "varchar", length=255)

User: "Create a GET /users endpoint"
You: Call create_endpoint("get_users", "/users", "GET", description="List all users")

User: "Create a POST /users endpoint with UserCreate request model"
You: Call create_model("UserCreate", {"name": {"type": "str", "required": true}, "email": {"type": "str", "required": true}}), then create_endpoint("create_user", "/users", "POST", request="UserCreate")

User: "Add product entity"
You: First call list_tables() to check if 'product' table exists. If it exists, call create_entity_crud("product"). If not, ask user if they want to create the table first.

User: "Create entity for user"
You: First call list_tables() to verify 'user' table exists, then call create_entity_crud("user").

User: "Create a user list page"
You: Call create_page("user_list", "User List", "Page to view all users"), then add_component("user_list", "table", "userTable", "Users", endpoint="users_list")

User: "Create a form to create users"
You: Call create_page("user_create", "Create User", "Form to create new users"), then add_component("user_create", "form", "userForm", "User Form", endpoint="users_create")

User: "Create pages for the product entity"
You: First call list_endpoints() to find product endpoints. Then create pages:
- create_page("product_list", "Products", "List all products")
- add_component("product_list", "table", "productTable", endpoint="product_list")
- create_page("product_detail", "Product Details", "View product details")
- add_component("product_detail", "detail", "productDetail", endpoint="product_get")

IMPORTANT: Always provide ALL required arguments."""
        },
        {"role": "user", "content": user_message}
    ]

    iteration = 0
    while iteration < max_iterations:
        iteration += 1

        # Call Ollama
        response = client.chat(
            model=CONFIG["ollama_model"],
            messages=messages,
            tools=tools,
        )

        assistant_message = response.get("message", {})
        messages.append(assistant_message)

        # Check if model wants to use tools
        tool_calls = extract_tool_calls({"message": assistant_message})

        if not tool_calls:
            # No tool calls - return the final response
            return assistant_message.get("content", "Task completed.")

        # Execute each tool call
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            arguments = tool_call["function"]["arguments"]

            print(f"  [Tool Call] {tool_name}({json.dumps(arguments)})")

            # Execute the tool
            result = execute_tool_call(tool_name, arguments)
            print(f"  [Result] {json.dumps(result)}")

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "content": json.dumps(result)
            })

    return "Max iterations reached. Task may not be complete."


def load_instructions(filepath: str) -> dict:
    """
    Load instructions from a YAML or text file.

    For .yaml files: returns the full YAML structure with schema and instructions.
    For .txt files: returns dict with instructions as prompts (one per line).

    Lines starting with # are treated as comments and skipped.
    Empty lines are ignored.
    """
    path = Path(filepath)

    if path.suffix == ".txt":
        instructions = []
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    instructions.append({"prompt": line})
        return {"instructions": instructions}

    # Default: treat as YAML
    with open(filepath, "r") as f:
        data = yaml.safe_load(f)
        return data if data else {}


def execute_instructions_file(filepath: str) -> None:
    """
    Execute instructions from a YAML or text file.

    Text files (.txt):
        - Each non-empty line is a natural language prompt
        - Lines starting with # are comments (ignored)
        - All prompts processed by LLM

    YAML files (.yaml/.yml):
        - schema: Path to schema file (optional, overrides SCHEMA_FILE env var)
        - endpoints: Path to endpoints file (optional, overrides ENDPOINTS_FILE env var)
        - ui: Path to UI file (optional, overrides UI_FILE env var)
        - instructions: List of instructions, each can be:
            - prompt: Natural language (processed by LLM)
            - tool + params: Direct tool call (executed immediately)
    """
    data = load_instructions(filepath)

    # Override schema file if specified
    if "schema" in data:
        schema_tools.SCHEMA_FILE = Path(data["schema"])
        CONFIG["schema_file"] = Path(data["schema"])
        print(f"Using schema file: {schema_tools.SCHEMA_FILE}")

    # Override endpoints file if specified
    if "endpoints" in data:
        endpoint_tools.ENDPOINTS_FILE = Path(data["endpoints"])
        CONFIG["endpoints_file"] = Path(data["endpoints"])
        print(f"Using endpoints file: {endpoint_tools.ENDPOINTS_FILE}")

    # Override UI file if specified
    if "ui" in data:
        ui_tools.UI_FILE = Path(data["ui"])
        CONFIG["ui_file"] = Path(data["ui"])
        print(f"Using UI file: {ui_tools.UI_FILE}")

    instructions = data.get("instructions", [])

    if not instructions:
        print("No instructions found in file.")
        return

    print(f"Executing {len(instructions)} instructions...\n")

    for i, instruction in enumerate(instructions, 1):
        if "prompt" in instruction:
            # Natural language prompt - use LLM
            print(f"[{i}] Prompt: {instruction['prompt']}")
            response = run_agent(instruction["prompt"])
            print(f"  {response}\n")

        elif "tool" in instruction:
            # Direct tool call - execute immediately
            tool_name = instruction["tool"]
            params = instruction.get("params", {})
            print(f"[{i}] Tool: {tool_name}({json.dumps(params)})")
            result = execute_tool_call(tool_name, params)
            print(f"  Result: {json.dumps(result)}\n")

        else:
            print(f"[{i}] Unknown instruction format: {instruction}")


def interactive_session():
    """Run an interactive session with the agent."""
    print("=" * 60)
    print(f"Schema, Endpoint & UI Agent (Ollama - {CONFIG['ollama_model']})")
    print(f"Host: {CONFIG['ollama_host']}")
    print(f"Schema: {CONFIG['schema_file']}")
    print(f"Endpoints: {CONFIG['endpoints_file']}")
    print(f"UI: {CONFIG['ui_file']}")
    print("=" * 60)
    print("\nType your request, or 'quit' to exit.\n")

    # Show current tables
    print("Current tables:")
    result = execute_tool_call("list_tables", {})
    if result.get("success") and result.get("data"):
        for table in result["data"]:
            print(f"  - {table}")
    else:
        print("  (none)")

    # Show current endpoints
    print("\nCurrent endpoints:")
    result = execute_tool_call("list_endpoints", {})
    if result.get("success") and result.get("data"):
        for endpoint in result["data"]:
            print(f"  - {endpoint}")
    else:
        print("  (none)")

    # Show current pages
    print("\nCurrent pages:")
    result = execute_tool_call("list_pages", {})
    if result.get("success") and result.get("data"):
        for page in result["data"]:
            print(f"  - {page}")
    else:
        print("  (none)")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print()
        response = run_agent(user_input)
        print(f"\nAgent: {response}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Schema, endpoint, and UI management agent using Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python example_tool_usage.py                           # Interactive mode
    python example_tool_usage.py "Create a users table"    # Single prompt
    python example_tool_usage.py -f instructions.yaml      # YAML instructions
    python example_tool_usage.py -f instructions.txt       # Text file (one prompt per line)
        """
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Path to instructions file (YAML or TXT)"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default=CONFIG["ollama_model"],
        help=f"Ollama model to use (default: {CONFIG['ollama_model']})"
    )
    parser.add_argument(
        "-s", "--schema",
        type=str,
        help="Path to schema YAML file (overrides SCHEMA_FILE env var)"
    )
    parser.add_argument(
        "-e", "--endpoints",
        type=str,
        help="Path to endpoints YAML file (overrides ENDPOINTS_FILE env var)"
    )
    parser.add_argument(
        "-u", "--ui",
        type=str,
        help="Path to UI YAML file (overrides UI_FILE env var)"
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Natural language prompt (if not using -f)"
    )

    args = parser.parse_args()

    # Override model if specified
    if args.model:
        CONFIG["ollama_model"] = args.model

    # Override schema file if specified
    if args.schema:
        schema_tools.SCHEMA_FILE = Path(args.schema)
        CONFIG["schema_file"] = Path(args.schema)

    # Override endpoints file if specified
    if args.endpoints:
        endpoint_tools.ENDPOINTS_FILE = Path(args.endpoints)
        CONFIG["endpoints_file"] = Path(args.endpoints)

    # Override UI file if specified
    if args.ui:
        ui_tools.UI_FILE = Path(args.ui)
        CONFIG["ui_file"] = Path(args.ui)

    if args.file:
        # Execute instructions file
        execute_instructions_file(args.file)

    elif args.prompt:
        # Single prompt mode
        user_message = " ".join(args.prompt)
        print(f"Request: {user_message}\n")
        response = run_agent(user_message)
        print(f"\n{response}")

    else:
        # Interactive mode
        interactive_session()


if __name__ == "__main__":
    main()