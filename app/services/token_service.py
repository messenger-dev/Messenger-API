from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from jose import JWTError, jwt

from app.core.config import settings
from app.core.redis import RedisClient


class TokenService:
    def __init__(self, redis_client: RedisClient | None = None) -> None:
        self.redis_client = redis_client
        self._local_revocation_store: dict[str, float] = {}

    def create_access_token(self, subject: str) -> str:
        current_time = datetime.now(timezone.utc)
        expiry_time = current_time + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload: dict[str, Any] = {
            "jti": str(uuid.uuid4()),
            "sub": str(subject),
            "exp": expiry_time,
            "iat": current_time,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError as error:
            raise ValueError(f"Invalid token: {error}") from error

    def revoke_token(self, token: str) -> None:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            return

        expires_at = payload.get("exp")

        jti = payload.get("jti")

        if not expires_at:
            remaining_seconds = None
        else:
            now_timestamp = datetime.now(timezone.utc).timestamp()
            remaining_seconds = int(expires_at - now_timestamp)
            if remaining_seconds <= 0:
                return

        token_identifier = jti if jti is not None else token

        if self.redis_client:
            redis_key = f"revoked_token:{token_identifier}"

            if remaining_seconds is not None and remaining_seconds > 0:
                self.redis_client.setex(redis_key, remaining_seconds, "1")
            else:
                self.redis_client.set(redis_key, "1")

        else:
            if remaining_seconds is not None:
                expiry_timestamp = datetime.now(timezone.utc).timestamp() + remaining_seconds
            else:
                expiry_timestamp = datetime.now(timezone.utc).timestamp() + 3153600000

            self._local_revocation_store[token_identifier] = expiry_timestamp

    def is_token_revoked(self, token: str) -> bool:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            return True

        expires_at = payload.get("exp")
        subject = payload.get("sub")
        if subject is None:
            return True

        jti = payload.get("jti")
        token_identifier = jti if jti is not None else token

        if self.redis_client:
            redis_key = f"revoked_token:{token_identifier}"
            return bool(self.redis_client.exists(redis_key))

        expiry_timestamp = self._local_revocation_store.get(token_identifier)
        if expiry_timestamp is None:
            return False

        current_timestamp = datetime.now(timezone.utc).timestamp()
        if current_timestamp > expiry_timestamp:
            del self._local_revocation_store[token_identifier]
            return False
        return True

    def _cleanup_expired_local_revocations(self) -> None:
        current_timestamp = datetime.now(timezone.utc).timestamp()
        expired_keys = [
            identifier for identifier, expiry_ts in self._local_revocation_store.items()
            if current_timestamp > expiry_ts
        ]
        for identifier in expired_keys:
            del self._local_revocation_store[identifier]