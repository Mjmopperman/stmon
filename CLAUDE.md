# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI backend application with PostgreSQL database and Hasura GraphQL integration, deployed to Oracle Cloud VMs via GitHub Actions.

**Architecture:**
- **FastAPI** backend (Python 3.11) with SQLAlchemy async ORM
- **PostgreSQL** database (Postgres 15)
- **Hasura GraphQL Engine** provides a GraphQL API layer over the database
- Two-VM deployment: Database on VM 1 (92.4.143.135), Application on VM 2 (129.151.184.220)

## Development Commands

```bash
# Local development (requires .env file with DB_* and HASURA_* variables)
docker compose -f docker-compose.db.yml up -d          # Start PostgreSQL
docker compose -f docker-compose.app-local.yml up -d   # Start FastAPI + Hasura (with hot reload)

# Stop services
docker compose -f docker-compose.app-local.yml down
docker compose -f docker-compose.db.yml down

# View logs
docker logs -f fastapi-backend
docker logs -f hasura
```

## Project Structure

```
app/
├── main.py          # FastAPI app, routes, startup events
├── config.py        # Pydantic settings from .env
├── database.py      # SQLAlchemy async engine setup
├── models.py        # SQLAlchemy model definitions
├── hasura.py        # Hasura GraphQL client wrapper
└── routers/
    └── users.py     # User CRUD endpoints + Hasura query example

db/
└── init.sql         # Database schema and seed data (runs on first container start)

schema/
├── database.yaml    # YAML schema definition (source of truth for tables/fields)
└── endpoints.yaml   # YAML endpoint definitions (FastAPI routes)

instructions/
├── example.yaml     # Example YAML instructions (prompts + tool calls)
└── example.txt      # Example text instructions (one prompt per line)

deploy/               # VM setup scripts (one-time provisioning)
.github/workflows/    # CI/CD: deploys on push to master/main

schema_tools.py           # CRUD tools for managing database.yaml
endpoint_tools.py         # CRUD tools for managing endpoints.yaml
example_tool_usage.py     # Ollama agent for natural language schema/endpoint editing
```

## Key Patterns

**Configuration:** Uses `pydantic-settings` with `.env` file. Required variables: `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, `DB_PORT`, `HASURA_ADMIN_SECRET`, `HASURA_URL`.

**Database Access:**
- SQLAlchemy async sessions via `get_db()` dependency
- Tables auto-created from models on startup (`Base.metadata.create_all`)
- Initial schema seeded by `db/init.sql`

**Hasura Integration:**
- Hasura runs in Docker alongside FastAPI
- FastAPI can query Hasura via `hasura_client.query(graphql_string, variables=dict)`
- Hasura console available at port 8080

**Deployment:**
- GitHub Actions workflow triggers on push to master/main
- Database VM: `docker-compose.db.yml` (persistent volume for data)
- Application VM: `docker-compose.app.yml` (builds fresh, runs health check)

## Schema Management Tools

The project includes tools for managing `schema/database.yaml` and `schema/endpoints.yaml` via LLM-powered agents.

### schema_tools.py
CRUD operations for YAML-based schema definitions:
- **Tables**: `create_table`, `read_table`, `update_table`, `delete_table`, `list_tables`
- **Fields**: `create_field`, `read_field`, `update_field`, `delete_field`, `list_fields`
- **Convenience**: `create_uuid_primary_key(table, name="id")` - adds UUID primary key with `gen_random_uuid()` default
- Schema persisted to `schema/database.yaml`
- Returns dict with `success` boolean and `message` or `data`

### endpoint_tools.py
CRUD operations for YAML-based endpoint definitions:
- **Endpoints**: `create_endpoint`, `read_endpoint`, `update_endpoint`, `delete_endpoint`, `list_endpoints`
- **Filtering**: `list_endpoints_by_method`, `list_endpoints_by_tag`
- **Models**: `create_model`, `read_model`, `update_model`, `delete_model`, `list_models`, `add_model_field`
- **Entity CRUD**: `create_entity_crud(table)` - creates model + 5 standard endpoints from a database table
- Endpoints persisted to `schema/endpoints.yaml`
- Returns dict with `success` boolean and `message` or `data`

### Endpoints and Models Relationship

The `endpoints.yaml` file has two sections that work together:

1. **endpoints**: Define API routes (path, method, request/response model names)
2. **models**: Define Pydantic schemas referenced by endpoints

When an endpoint specifies `request: SomeModel` or `response: SomeModel`, that model
must exist in the `models` section with matching field definitions.

Example:
```yaml
endpoints:
  complex_list:
    path: /complex/list
    method: GET
    response: Complex[]    # references model below, [] indicates array

models:
  Complex:
    description: Response model for complex properties
    fields:
      id:
        type: uuid
        required: true
      name:
        type: str
        required: true
```

**Type mapping (database → Pydantic):**
- serial/integer → int
- uuid → uuid
- varchar/text → str
- timestamp → datetime
- boolean → bool
- decimal → float

**Important:** When creating an endpoint with a response model, always create the model
first using `create_model` before (or alongside) `create_endpoint`. Multi-step instructions
like "create a model AND create an endpoint" may be partially executed by the LLM — verify
both steps completed.

### Endpoint Naming Convention

Endpoint names follow this format: `{entity}_{action}` or `{entity}_{action}_id`

- **entity**: singular noun (e.g., `complex`, `user`, `order`)
- **action**: verb describing the operation (e.g., `list`, `get`, `create`, `update`, `delete`)
- **_id**: suffix for operations on a specific item by ID

Examples:
```
complex_list        → GET /complex/list           (list all)
complex_get_id      → GET /complex/get/{id}       (get one)
complex_create      → POST /complex/create        (create)
complex_update_id   → POST /complex/update/{id}   (update one)
complex_delete_id   → DELETE /complex/delete/{id} (delete one)
```

**Rules:**
- Entity is always singular, not plural (`complex`, not `complexes`)
- Use `list` for collection GETs, `get_id` for single item GETs
- Append `_id` suffix when the path includes an ID parameter

### example_tool_usage.py
Ollama-based agent for natural language schema and endpoint management:

```bash
# Interactive mode
python example_tool_usage.py

# Single prompt
python example_tool_usage.py "Create a users table with id and email"

# Instructions file (YAML or TXT)
python example_tool_usage.py -f instructions.yaml
python example_tool_usage.py -f instructions.txt
```

**Environment variables:**
- `OLLAMA_HOST` - Ollama server URL (default: http://localhost:11434)
- `OLLAMA_API_KEY` - API key for hosted Ollama (optional)
- `OLLAMA_MODEL` - Model to use (default: qwen2.5-coder:7b)
- `SCHEMA_FILE` - Path to schema YAML (default: schema/database.yaml)
- `ENDPOINTS_FILE` - Path to endpoints YAML (default: schema/endpoints.yaml)

### Instructions File Format

**Text file (.txt)** - One prompt per line, simpler format:
```
# Comments start with #
Create a users table with id and email
Add a created_at timestamp to users
List all tables
```

**YAML file (.yaml)** - Mixed prompts and direct tool calls:
```yaml
schema: schema/database.yaml
endpoints: schema/endpoints.yaml
instructions:
  - prompt: "Create an orders table with id, user_id, total, status"
  - tool: create_field
    params:
      table: orders
      name: created_at
      type: timestamp
```

## Development Methodology

This project follows a YAML-first, contract-driven approach.
Specifications are the source of truth — code is generated from
them, never the reverse.

### YAML Specification Structure
- `schema/tables/`         → table definitions → PostgreSQL migrations
- `schema/hasura/actions/` → Hasura action definitions → metadata
- `api/endpoints/`         → FastAPI route contracts → handler stubs
- `api/functions/`         → pure computational logic → Python functions
- `ui/pages/`              → page layout contracts → Alpine.js components

### Build Queue
- `build/queue.yaml`  → ordered list of pending implementation tasks
- `build/output/`     → generated code awaiting human review
- Run `python orchestrator.py` to process next pending task
- Review output before running `python deployer.py` to place files

### AI Session Handoff
At end of each session update this file with:
- What was just completed
- What the next pending task is
- Any architectural decisions made

## Build Queue Status
- Orchestrator: operational (v0.1.0)
- Last completed: T001 test_table migration SQL
- Next: Add real ESC specs to queue
- Deployer: not yet built (v0.2.0 roadmap)

## Build Queue Rules

The build queue lives in `build/queue.yaml`.

### Adding a new task
1. Write the YAML spec file first — the orchestrator will fail if it does not exist
2. Add the task to `build/queue.yaml` with status `pending`
3. Run `python -m esc_orchestrator`

### Task fields
- `id` — unique, increment T001, T002, T003 etc.
- `status` — always `pending` for new tasks
- `yaml` — path to spec file relative to project root
- `prompt` — one-line instruction from the table below
- Never add `output` or set `status: done` — orchestrator handles both

### Valid prompts by task type

| kind                | prompt                                                          |
|---------------------|-----------------------------------------------------------------|
| table               | Generate the PostgreSQL migration SQL for this table            |
| hasura_action       | Generate the Hasura action metadata JSON                        |
| hasura_permission   | Generate the Hasura permission metadata JSON for this table and role |
| hasura_relationship | Generate the Hasura relationship metadata JSON                  |
| endpoint            | Generate the FastAPI route with Pydantic input and output models |
| function            | Generate the pure Python function with unit tests               |
| page                | Generate the Alpine.js page component                           |
| component           | Generate the reusable Alpine.js component                       |

### Rules
- `## Session Update` is always the last section in this file
- Never put content below `## Session Update`
- Spec file must exist before adding task to queue

## Session Update

_Last updated: 2026-04-06_

### Completed
- **T001:** `schema/tables/test_table.yaml`
  Output: `build/output/T001_schema_tables_test_table.txt`
  Deployed: `db/migrations/002_create_test_table.sql`
- **Schema Tools:** Reviewed existing `schema_tools.py` and `example_tool_usage.py`
- **UUID Primary Key:** Added `create_uuid_primary_key()` convenience function to schema_tools.py
- **Text Instructions:** Modified `example_tool_usage.py` to support `.txt` files (one prompt per line)
- **Examples:** Created `instructions/example.txt` demonstrating text format

### Up Next
- Add real ESC table specs to queue
- Test schema_tools integration with orchestrator workflow