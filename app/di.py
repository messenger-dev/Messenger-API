"""Central dependency injection module for the application."""

from __future__ import annotations

from typing import Iterator

from fastapi import Depends
from sqlmodel import Session

from app.core.redis import get_redis_client, get_redis_pubsub
from app.interfaces.pubsub import PubSub
from app.core.security import get_current_user
from app.core.token import get_token_service
from app.db.session import get_session
from app.models import User

__all__ = [
    "get_db",
    "get_current_authenticated_user",
    "get_token_service",
    "get_redis_client",
    "get_pubsub",
]


def get_db() -> Iterator[Session]:
    """Provide a database session for the request lifecycle."""
    yield from get_session()


def get_current_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    """Provide the currently authenticated user."""
    return current_user


def get_pubsub() -> PubSub | None:
    """Provide a PubSub implementation (or None if not configured)."""
    return get_redis_pubsub()
