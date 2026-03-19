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

deploy/               # VM setup scripts (one-time provisioning)
.github/workflows/    # CI/CD: deploys on push to master/main
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

_Last updated: —_

### Completed
- Nothing yet.

### Up Next
- T001: schema/tables/test_table.yaml