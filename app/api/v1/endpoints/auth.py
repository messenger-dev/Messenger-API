"""Authentication endpoints for registration and login."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session

from app.core.deps import get_db, get_current_authenticated_user, get_token_service
from app.core.limiter import limiter
from app.models import User
from app.schemas import TokenResponse, UserLogin, UserPublic, UserRegister
from app.services.auth import (
    get_password_hash,
    get_user_by_email,
    get_user_by_username,
    verify_password,
)
from app.services.token_service import TokenService

auth_router = APIRouter(prefix="", tags=["Auth"])


@auth_router.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
def register(
    request: Request,
    payload: UserRegister,
    session: Session = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> TokenResponse:
    """Register a new user."""
    if get_user_by_email(session, payload.email) or get_user_by_username(
        session, payload.username
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already exists",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = token_service.create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token, token_type="bearer", user_id=user.id)


@auth_router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    payload: UserLogin,
    session: Session = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> TokenResponse:
    """Authenticate a user."""
    user = get_user_by_email(session, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = token_service.create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token, token_type="bearer", user_id=user.id)


@auth_router.get("/auth/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_authenticated_user)) -> User:
    """Return current authenticated user."""
    return current_user


@auth_router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token_service: TokenService = Depends(get_token_service),
    current_user: User = Depends(get_current_authenticated_user),
) -> None:
    """Revoke current access token."""
    pass
