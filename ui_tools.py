#!/usr/bin/env python3
"""
ui_tools.py
───────────
CRUD operations for UI page definitions.

Pages define the user interface structure with components.
Each page references use cases and endpoints.

Usage:
    python ui_tools.py check
    python ui_tools.py check <page_name>

    python ui_tools.py add_page      <name> <title> <description> <primary_actor>
    python ui_tools.py set_use_case  <page> <use_case>
    python ui_tools.py add_component <page> <type> <id> <title>

    python ui_tools.py get_page      <name>
    python ui_tools.py list_pages
    python ui_tools.py delete_page   <name>
"""

import os
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configuration - can be overridden via environment variables
UI_FILE = Path(os.getenv("UI_FILE", "schema/ui.yaml"))

# Valid component types
VALID_COMPONENT_TYPES = {
    "form", "detail", "table", "list", "card", "modal",
    "tabs", "wizard", "chart", "map", "calendar", "upload"
}


def _load_ui() -> dict:
    """Load the UI YAML file."""
    if not UI_FILE.exists():
        return {"pages": {}}
    with open(UI_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data if data else {"pages": {}}


def _save_ui(data: dict) -> None:
    """Save the UI to YAML file."""
    UI_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(UI_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


# =============================================================================
# PAGE CRUD
# =============================================================================


def create_page(
    name: str,
    title: str,
    description: Optional[str] = None,
    primary_actor: Optional[str] = None,
    use_case: Optional[str] = None,
    auth_required: bool = False,
    layout: Optional[str] = None,
) -> dict:
    """
    Create a new page definition.

    Args:
        name: Page identifier (unique, used as filename)
        title: Display title for the page
        description: Optional page description
        primary_actor: Primary user role for this page
        use_case: Associated use case ID
        auth_required: Whether authentication is required
        layout: Page layout type (default, sidebar, tabs, wizard)

    Returns:
        Result dict with success status and message
    """
    ui = _load_ui()

    if name in ui.get("pages", {}):
        return {"success": False, "message": f"Page '{name}' already exists"}

    page_def = {
        "title": title,
        "components": [],
    }

    if description:
        page_def["description"] = description
    if primary_actor:
        page_def["primary_actor"] = primary_actor
    if use_case:
        page_def["use_case"] = use_case
    if auth_required:
        page_def["auth_required"] = True
    if layout:
        page_def["layout"] = layout

    ui.setdefault("pages", {})[name] = page_def
    _save_ui(ui)

    return {"success": True, "message": f"Page '{name}' created", "data": page_def}


def read_page(name: str) -> dict:
    """
    Read a page definition.

    Args:
        name: Page identifier

    Returns:
        Result dict with success status and page data or error message
    """
    ui = _load_ui()

    if name not in ui.get("pages", {}):
        return {"success": False, "message": f"Page '{name}' not found"}

    return {"success": True, "data": ui["pages"][name]}


def update_page(
    name: str,
    new_name: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    primary_actor: Optional[str] = None,
    use_case: Optional[str] = None,
    auth_required: Optional[bool] = None,
    layout: Optional[str] = None,
) -> dict:
    """
    Update a page definition.

    Args:
        name: Current page identifier
        new_name: New page identifier (optional)
        title: New title (optional)
        description: New description (optional)
        primary_actor: New primary actor (optional)
        use_case: New use case reference (optional)
        auth_required: New auth requirement (optional)
        layout: New layout type (optional)

    Returns:
        Result dict with success status and message
    """
    ui = _load_ui()

    if name not in ui.get("pages", {}):
        return {"success": False, "message": f"Page '{name}' not found"}

    page = ui["pages"][name]

    # Handle rename
    if new_name and new_name != name:
        if new_name in ui["pages"]:
            return {"success": False, "message": f"Page '{new_name}' already exists"}
        ui["pages"][new_name] = page
        del ui["pages"][name]
        name = new_name

    # Update fields
    if title is not None:
        page["title"] = title
    if description is not None:
        page["description"] = description
    if primary_actor is not None:
        page["primary_actor"] = primary_actor
    if use_case is not None:
        page["use_case"] = use_case
    if auth_required is not None:
        if auth_required:
            page["auth_required"] = True
        else:
            page.pop("auth_required", None)
    if layout is not None:
        page["layout"] = layout

    _save_ui(ui)
    return {"success": True, "message": f"Page '{name}' updated"}


def delete_page(name: str) -> dict:
    """
    Delete a page definition.

    Args:
        name: Page identifier

    Returns:
        Result dict with success status and message
    """
    ui = _load_ui()

    if name not in ui.get("pages", {}):
        return {"success": False, "message": f"Page '{name}' not found"}

    del ui["pages"][name]
    _save_ui(ui)

    return {"success": True, "message": f"Page '{name}' deleted"}


def list_pages() -> dict:
    """
    List all page names.

    Returns:
        Result dict with success status and list of page names
    """
    ui = _load_ui()
    return {"success": True, "data": list(ui.get("pages", {}).keys())}


def list_pages_by_actor(actor: str) -> dict:
    """
    List all pages for a specific primary actor.

    Args:
        actor: Primary actor to filter by

    Returns:
        Result dict with success status and list of page names
    """
    ui = _load_ui()

    matching = [
        name for name, defn in ui.get("pages", {}).items()
        if defn.get("primary_actor") == actor
    ]

    return {"success": True, "data": matching}


def list_pages_by_use_case(use_case: str) -> dict:
    """
    List all pages for a specific use case.

    Args:
        use_case: Use case ID to filter by

    Returns:
        Result dict with success status and list of page names
    """
    ui = _load_ui()

    matching = [
        name for name, defn in ui.get("pages", {}).items()
        if defn.get("use_case") == use_case
    ]

    return {"success": True, "data": matching}


# =============================================================================
# COMPONENT CRUD
# =============================================================================


def add_component(
    page: str,
    component_type: str,
    component_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    endpoint: Optional[str] = None,
    model: Optional[str] = None,
    fields: Optional[List[str]] = None,
    actions: Optional[List[Dict[str, str]]] = None,
    props: Optional[Dict[str, Any]] = None,
    position: Optional[int] = None,
) -> dict:
    """
    Add a component to a page.

    Args:
        page: Page name
        component_type: Type of component (form, detail, table, list, etc.)
        component_id: Unique component identifier within the page
        title: Component display title
        description: Optional component description
        endpoint: Associated endpoint name for data fetching
        model: Associated model name for forms
        fields: List of fields to display/edit
        actions: List of action buttons (label, action pairs)
        props: Additional component-specific properties
        position: Position in page (default: append at end)

    Returns:
        Result dict with success status and message
    """
    component_type = component_type.lower()
    if component_type not in VALID_COMPONENT_TYPES:
        return {
            "success": False,
            "message": f"Invalid component type '{component_type}'. Must be one of: {', '.join(sorted(VALID_COMPONENT_TYPES))}"
        }

    ui = _load_ui()

    if page not in ui.get("pages", {}):
        return {"success": False, "message": f"Page '{page}' not found"}

    components = ui["pages"][page].setdefault("components", [])

    # Check for duplicate component ID
    if any(c.get("id") == component_id for c in components):
        return {"success": False, "message": f"Component '{component_id}' already exists in page '{page}'"}

    component_def = {
        "type": component_type,
        "id": component_id,
    }

    if title:
        component_def["title"] = title
    if description:
        component_def["description"] = description
    if endpoint:
        component_def["endpoint"] = endpoint
    if model:
        component_def["model"] = model
    if fields:
        component_def["fields"] = fields
    if actions:
        component_def["actions"] = actions
    if props:
        component_def["props"] = props

    if position is not None and 0 <= position < len(components):
        components.insert(position, component_def)
    else:
        components.append(component_def)

    _save_ui(ui)
    return {"success": True, "message": f"Component '{component_id}' added to page '{page}'", "data": component_def}


def get_component(page: str, component_id: str) -> dict:
    """
    Get a component definition from a page.

    Args:
        page: Page name
        component_id: Component identifier

    Returns:
        Result dict with success status and component data or error message
    """
    ui = _load_ui()

    if page not in ui.get("pages", {}):
        return {"success": False, "message": f"Page '{page}' not found"}

    for component in ui["pages"][page].get("components", []):
        if component.get("id") == component_id:
            return {"success": True, "data": component}

    return {"success": False, "message": f"Component '{component_id}' not found in page '{page}'"}


def update_component(
    page: str,
    component_id: str,
    new_id: Optional[str] = None,
    component_type: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    endpoint: Optional[str] = None,
    model: Optional[str] = None,
    fields: Optional[List[str]] = None,
    actions: Optional[List[Dict[str, str]]] = None,
    props: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Update a component definition.

    Args:
        page: Page name
        component_id: Current component identifier
        new_id: New component identifier (optional)
        component_type: New component type (optional)
        title: New title (optional)
        description: New description (optional)
        endpoint: New associated endpoint (optional)
        model: New associated model (optional)
        fields: New fields list (optional)
        actions: New actions list (optional)
        props: New props dict (optional)

    Returns:
        Result dict with success status and message
    """
    ui = _load_ui()

    if page not in ui.get("pages", {}):
        return {"success": False, "message": f"Page '{page}' not found"}

    components = ui["pages"][page].get("components", [])
    component = None
    component_idx = -1

    for idx, c in enumerate(components):
        if c.get("id") == component_id:
            component = c
            component_idx = idx
            break

    if component is None:
        return {"success": False, "message": f"Component '{component_id}' not found in page '{page}'"}

    # Handle ID rename
    if new_id and new_id != component_id:
        if any(c.get("id") == new_id for c in components):
            return {"success": False, "message": f"Component '{new_id}' already exists in page '{page}'"}
        component["id"] = new_id

    # Update fields
    if component_type:
        component_type = component_type.lower()
        if component_type not in VALID_COMPONENT_TYPES:
            return {
                "success": False,
                "message": f"Invalid component type '{component_type}'. Must be one of: {', '.join(sorted(VALID_COMPONENT_TYPES))}"
            }
        component["type"] = component_type

    if title is not None:
        component["title"] = title
    if description is not None:
        component["description"] = description
    if endpoint is not None:
        component["endpoint"] = endpoint
    if model is not None:
        component["model"] = model
    if fields is not None:
        component["fields"] = fields
    if actions is not None:
        component["actions"] = actions
    if props is not None:
        component["props"] = props

    _save_ui(ui)
    return {"success": True, "message": f"Component '{component_id}' updated in page '{page}'"}


def remove_component(page: str, component_id: str) -> dict:
    """
    Remove a component from a page.

    Args:
        page: Page name
        component_id: Component identifier

    Returns:
        Result dict with success status and message
    """
    ui = _load_ui()

    if page not in ui.get("pages", {}):
        return {"success": False, "message": f"Page '{page}' not found"}

    components = ui["pages"][page].get("components", [])
    original_len = len(components)

    ui["pages"][page]["components"] = [c for c in components if c.get("id") != component_id]

    if len(ui["pages"][page]["components"]) == original_len:
        return {"success": False, "message": f"Component '{component_id}' not found in page '{page}'"}

    _save_ui(ui)
    return {"success": True, "message": f"Component '{component_id}' removed from page '{page}'"}


def list_components(page: str) -> dict:
    """
    List all components in a page.

    Args:
        page: Page name

    Returns:
        Result dict with success status and list of component data
    """
    ui = _load_ui()

    if page not in ui.get("pages", {}):
        return {"success": False, "message": f"Page '{page}' not found"}

    components = ui["pages"][page].get("components", [])
    return {"success": True, "data": components}


def move_component(page: str, component_id: str, position: int) -> dict:
    """
    Move a component to a new position in the page.

    Args:
        page: Page name
        component_id: Component identifier
        position: New position (0-based index)

    Returns:
        Result dict with success status and message
    """
    ui = _load_ui()

    if page not in ui.get("pages", {}):
        return {"success": False, "message": f"Page '{page}' not found"}

    components = ui["pages"][page].get("components", [])

    # Find current position
    current_idx = None
    for idx, c in enumerate(components):
        if c.get("id") == component_id:
            current_idx = idx
            break

    if current_idx is None:
        return {"success": False, "message": f"Component '{component_id}' not found in page '{page}'"}

    # Clamp position to valid range
    position = max(0, min(position, len(components) - 1))

    if position == current_idx:
        return {"success": True, "message": f"Component '{component_id}' already at position {position}"}

    # Move component
    component = components.pop(current_idx)
    components.insert(position, component)

    _save_ui(ui)
    return {"success": True, "message": f"Component '{component_id}' moved to position {position}"}


# =============================================================================
# PAGE FROM ENTITY (convenience)
# =============================================================================


def create_page_from_endpoint(
    endpoint_name: str,
    page_name: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    primary_actor: Optional[str] = None,
) -> dict:
    """
    Create a page from an endpoint definition.

    This creates a page with an appropriate component based on the endpoint method:
    - GET (list) → table component
    - GET (single) → detail component
    - POST/PUT → form component

    Args:
        endpoint_name: Name of the endpoint to create page from
        page_name: Optional page name (default: derived from endpoint)
        title: Optional title (default: derived from endpoint)
        description: Optional description
        primary_actor: Optional primary actor

    Returns:
        Result dict with success status and details
    """
    # Load endpoints to get endpoint info
    from endpoint_tools import read_endpoint

    ep_result = read_endpoint(endpoint_name)
    if not ep_result.get("success"):
        return {"success": False, "message": f"Endpoint '{endpoint_name}' not found"}

    endpoint = ep_result["data"]
    method = endpoint.get("method", "GET").upper()
    path = endpoint.get("path", "/")

    # Derive page name and title
    if not page_name:
        page_name = endpoint_name.replace("_", "-")

    if not title:
        # Convert snake_case to Title Case
        title = endpoint_name.replace("_", " ").title()

    # Create page
    page_result = create_page(
        name=page_name,
        title=title,
        description=description or endpoint.get("description", ""),
        primary_actor=primary_actor,
    )

    if not page_result.get("success"):
        return page_result

    # Determine component type based on method
    if method == "GET":
        if "{id}" in path:
            component_type = "detail"
        else:
            component_type = "table"
    elif method in ("POST", "PUT", "PATCH"):
        component_type = "form"
    else:
        component_type = "detail"

    # Add component
    component_result = add_component(
        page=page_name,
        component_type=component_type,
        component_id=f"{endpoint_name}_component",
        title=title,
        endpoint=endpoint_name,
    )

    if not component_result.get("success"):
        # Rollback page creation
        delete_page(page_name)
        return component_result

    return {
        "success": True,
        "message": f"Page '{page_name}' created from endpoint '{endpoint_name}'",
        "page": page_name,
        "component_type": component_type,
    }


# =============================================================================
# TOOL REGISTRY (for LLM use)
# =============================================================================


TOOLS = [
    # Pages
    {"name": "create_page", "function": create_page,
     "description": "Create a new UI page definition"},
    {"name": "read_page", "function": read_page,
     "description": "Read a page definition"},
    {"name": "update_page", "function": update_page,
     "description": "Update a page definition"},
    {"name": "delete_page", "function": delete_page,
     "description": "Delete a page definition"},
    {"name": "list_pages", "function": list_pages,
     "description": "List all page names"},
    {"name": "list_pages_by_actor", "function": list_pages_by_actor,
     "description": "List pages filtered by primary actor"},
    {"name": "list_pages_by_use_case", "function": list_pages_by_use_case,
     "description": "List pages filtered by use case"},

    # Components
    {"name": "add_component", "function": add_component,
     "description": "Add a component to a page"},
    {"name": "get_component", "function": get_component,
     "description": "Get a component definition"},
    {"name": "update_component", "function": update_component,
     "description": "Update a component definition"},
    {"name": "remove_component", "function": remove_component,
     "description": "Remove a component from a page"},
    {"name": "list_components", "function": list_components,
     "description": "List all components in a page"},
    {"name": "move_component", "function": move_component,
     "description": "Move a component to a new position"},

    # Convenience
    {"name": "create_page_from_endpoint", "function": create_page_from_endpoint,
     "description": "Create a page from an existing endpoint definition"},
]


def get_tool(name: str) -> Optional[dict]:
    """Get a tool by name."""
    for tool in TOOLS:
        if tool["name"] == name:
            return tool
    return None


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    USAGE = """
Usage:
  python ui_tools.py check [<page_name>]

  python ui_tools.py add_page      <name> <title> <description> <primary_actor>
  python ui_tools.py set_use_case  <page> <use_case>
  python ui_tools.py add_component <page> <type> <id> <title>

  python ui_tools.py get_page      <name>
  python ui_tools.py list_pages
  python ui_tools.py delete_page   <name>
"""

    def check_page(page_name: str = None) -> None:
        ui = _load_ui()
        pages = ui.get("pages", {})

        if page_name:
            if page_name not in pages:
                print(f"Page '{page_name}' not found.")
                return
            page = pages[page_name]
            print(f"\n── Page: {page_name}")
            print(f"   Title    : {page.get('title', '—')}")
            print(f"   Actor    : {page.get('primary_actor', '—')}")
            print(f"   Use Case : {page.get('use_case', '—')}")
            print(f"   Layout   : {page.get('layout', 'default')}")
            print(f"   Auth     : {page.get('auth_required', False)}")
            print(f"   Components ({len(page.get('components', []))}):")
            for c in page.get("components", []):
                print(f"      [{c.get('type', '?')}] {c.get('id', '?')}: {c.get('title', '—')}")
            print()
        else:
            print(f"\nFile: {UI_FILE} ({len(pages)} pages)")
            for name, page in pages.items():
                comps = len(page.get("components", []))
                print(f"  {name:<30}  ({comps} comps)  {page.get('title', '—')}")
            print()

    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(USAGE)

    elif args[0] == "check":
        check_page(args[1] if len(args) > 1 else None)

    elif args[0] == "add_page" and len(args) >= 5:
        create_page(args[1], args[2], args[3], args[4])

    elif args[0] == "set_use_case" and len(args) >= 3:
        result = update_page(args[1], use_case=args[2])
        print(f"  {'✓' if result['success'] else '✗'}  {result['message']}")

    elif args[0] == "add_component" and len(args) >= 5:
        add_component(args[1], args[2], args[3], args[4])

    elif args[0] == "get_page" and len(args) >= 2:
        check_page(args[1])

    elif args[0] == "list_pages":
        result = list_pages()
        for name in result.get("data", []):
            print(f"  {name}")

    elif args[0] == "delete_page" and len(args) >= 2:
        result = delete_page(args[1])
        print(f"  {'✓' if result['success'] else '✗'}  {result['message']}")

    else:
        print(USAGE)