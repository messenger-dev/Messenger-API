from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = Field(default="bearer", json_schema_extra={"example": "bearer"})
    user_id:      int

    model_config = ConfigDict(from_attributes=True)
