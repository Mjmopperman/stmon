from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import users
from app.database import engine
from app.models import Base

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

@app.get("/")
async def root():
    return {"message": "API is running", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy", "database": "connected"}
