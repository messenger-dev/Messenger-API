"""User search endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.di import get_db, get_current_authenticated_user
from app.schemas import UserPublic
from app.models import User

users_router = APIRouter(prefix="", tags=["Users"])


@users_router.get("/users", response_model=list[UserPublic])
def search_users(
    q:            str = Query(..., min_length=2),
    limit:        int = Query(20, le=100),
    current_user: User        = Depends(get_current_authenticated_user),
    session:      Session     = Depends(get_db),
) -> list[User]:
    """Search users by username."""
    query = select(User).where(User.username.contains(q)).limit(limit)
    return session.exec(query).all()
