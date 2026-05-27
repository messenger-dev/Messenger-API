"""Schemas for sending email notifications."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmailSendRequest(BaseModel):
    recipient: EmailStr = Field(..., json_schema_extra={"example": "ivan@example.com"})
    subject:   str = Field(..., min_length=1, max_length=120, json_schema_extra={"example": "Welcome to Messenger"})
    body:      str = Field(..., min_length=1, max_length=5000, json_schema_extra={"example": "Hello!"})

    model_config = ConfigDict(from_attributes=True)
