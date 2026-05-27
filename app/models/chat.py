"""Chat model definitions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Chat(SQLModel, table=True):
    """Group or direct chat model."""

    id:         Optional[int] = Field(default=None, primary_key=True)
    name:       str = Field(nullable=False, max_length=100)
    is_group:   bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: int = Field(foreign_key="user.id")


class ChatParticipant(SQLModel, table=True):
    """Chat membership model."""

    chat_id:   int = Field(foreign_key="chat.id", primary_key=True)
    user_id:   int = Field(foreign_key="user.id", primary_key=True)
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
