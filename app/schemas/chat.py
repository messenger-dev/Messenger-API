from __future__ import annotations

from typing import Optional
from datetime import datetime
from app.schemas.user import UserPublic

from pydantic import BaseModel, ConfigDict, Field


class CreateChat(BaseModel):
    name:            str | None = Field(None, min_length=1, max_length=100, json_schema_extra={"example": "Project Team"})
    participant_ids: list[int] = Field(..., json_schema_extra={"example": [2, 3, 4]})
    is_group:        bool = True


class UpdateChat(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, json_schema_extra={"example": "Project Team"})


class UpdateChatParticipants(BaseModel):
    participant_ids: list[int] = Field(..., json_schema_extra={"example": [3, 4]})


class ChatLastMessage(BaseModel):
    text:            str
    sent_at:         datetime
    sender_username: str


class ChatPreview(BaseModel):
    id:                int
    name:              str
    is_group:          bool
    participant_count: int
    last_message:      Optional[ChatLastMessage] = None
    unread_count:      int
    updated_at:        datetime

    model_config = ConfigDict(from_attributes=True)


class ChatDetail(BaseModel):
    id:           int
    name:         str
    is_group:     bool
    participants: list[UserPublic]
    created_at:   datetime
    created_by:   int

    model_config = ConfigDict(from_attributes=True)
