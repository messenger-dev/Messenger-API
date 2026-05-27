from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, json_schema_extra={"example": "ivan"})
    email:    EmailStr = Field(..., json_schema_extra={"example": "ivan@example.com"})
    password: str = Field(..., min_length=4, json_schema_extra={"example": "secret123"})


class UserLogin(BaseModel):
    email:    EmailStr = Field(..., json_schema_extra={"example": "ivan@example.com"})
    password: str = Field(..., json_schema_extra={"example": "secret123"})


class UserPublic(BaseModel):
    id:         int
    username:   str
    email:      EmailStr
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
