"""JWT authentication and token verification."""

from __future__ import annotations

from sqlmodel import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models import User
from app.core.logging import logger
from app.db.session import get_session
from app.core.token import get_token_service
from app.services.token_service import TokenService


security = HTTPBearer()

def get_current_user(
    credentials:   HTTPAuthorizationCredentials = Depends(security),
    session:       Session = Depends(get_session),
    token_service: TokenService = Depends(get_token_service),
) -> User:
    """Resolve authenticated user from JWT token."""
    if credentials.scheme.lower() != "bearer":
        logger.warning("Auth failed: invalid scheme %s", credentials.scheme)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        if token_service.is_token_revoked(token):
            logger.warning("Auth failed: token revoked")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revoked",
            )
        payload = token_service.verify_token(token)
        
    except ValueError as e:
        logger.warning("Auth failed: invalid token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.isdigit():
        logger.warning("Auth failed: invalid 'sub' in token payload: %s", payload)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = session.get(User, int(user_id))
    if not user:
        logger.warning("Auth failed: user not found: %s", user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
