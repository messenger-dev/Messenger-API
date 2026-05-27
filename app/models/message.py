"""Message model definition."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    """Chat message model."""

    id:              Optional[int] = Field(default=None, primary_key=True)
    chat_id:         int = Field(foreign_key="chat.id")
    sender_id:       int = Field(foreign_key="user.id")
    sender_username: str
    text:            str = Field(nullable=False, max_length=2000)
    reply_to_id:     Optional[int] = Field(default=None, foreign_key="message.id")
    is_read:         bool = Field(default=False)
    sent_at:         datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
