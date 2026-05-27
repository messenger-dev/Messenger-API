"""User model definition."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User account model."""

    id:              Optional[int] = Field(default=None, primary_key=True)
    username:        str = Field(index=True, nullable=False, max_length=50)
    email:           str = Field(index=True, nullable=False)
    hashed_password: str
    avatar_url:      Optional[str] = None
    created_at:      datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
