"""TokenService singleton provider to avoid circular imports."""

from fastapi import Depends

from app.core.redis import get_redis_client
from app.services.token_service import TokenService

_token_service: TokenService | None = None


def get_token_service(redis_client=Depends(get_redis_client)) -> TokenService:
    """Provide a cached TokenService instance."""
    global _token_service
    if _token_service is None:
        _token_service = TokenService(redis_client)
    return _token_service
