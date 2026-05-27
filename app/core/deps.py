"""Compatibility layer exposing dependency helpers from the DI module."""

from app.di import get_db, get_current_authenticated_user, get_token_service

__all__ = ["get_db", "get_current_authenticated_user", "get_token_service"]
