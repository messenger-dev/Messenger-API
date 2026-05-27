from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SendMessage(BaseModel):
    text:        str = Field(..., min_length=1, max_length=2000, json_schema_extra={"example": "Hello there!"})
    reply_to_id: Optional[int] = Field(None, json_schema_extra={"example": None})


class MessageResponse(BaseModel):
    id:              int
    chat_id:         int
    sender_id:       int
    sender_username: str
    text:            str
    reply_to_id:     Optional[int] = None
    is_read:         bool
    sent_at:         datetime

    model_config = ConfigDict(from_attributes=True)


class ReadReceiptPayload(BaseModel):
    message_id: Optional[int] = None
