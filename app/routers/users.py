from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User
from app.hasura import hasura_client
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    name: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str

    class Config:
        from_attributes = True


class UserResponseWithDate(BaseModel):
    id: int
    email: str
    name: str
    created_at: Optional[str] = None

@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = User(email=user.email, name=user.name)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/users", response_model=List[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users-hasura/{user_id}", response_model=UserResponseWithDate)
async def get_user_from_hasura(user_id: int):
    """Get a specific user by ID from Hasura (includes created_at)."""
    query = """
    query GetUser($id: Int!) {
        users(where: {id: {_eq: $id}}) {
            id
            email
            name
            created_at
        }
    }
    """
    result = await hasura_client.query(query, variables={"id": user_id})

    users = result.get("data", {}).get("users", [])
    if not users:
        raise HTTPException(status_code=404, detail="User not found")

    return users[0]
