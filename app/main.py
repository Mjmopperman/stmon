from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import users
from app.database import engine
from app.models import Base
from app.hasura import hasura_client

app = FastAPI(
    title="My API",
    description="API with PostgreSQL + Hasura",
    version="1.0.0"
)

# CORS for Hasura
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/api", tags=["users"])

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/test")
async def test():
    return {"message": "Test endpoint is working. I am sure of it."}  


@app.get("/")
async def root():
    return {"message": "API is running", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy", "database": "connected"}


@app.get("/hasura-health")
async def hasura_health():
    """Check if Hasura is accessible from FastAPI."""
    try:
        # Simple introspection query to check if Hasura is responding
        result = await hasura_client.query("{ __typename }")
        return {
            "status": "connected",
            "hasura_response": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/hasura-query")
async def hasura_query(query: str):
    """Execute a custom GraphQL query against Hasura.

    Example query: { users { id email } }
    """
    try:
        result = await hasura_client.query(query)
        return result
    except Exception as e:
        return {"error": str(e)}
