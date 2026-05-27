class AppError(Exception):
    """Base class for application-specific exceptions."""


class NotFoundError(AppError):
    pass


class PermissionDeniedError(AppError):
    pass


class EmailServiceError(Exception):
    """Raised when email service operations fail."""
    pass


class InvalidWebSocketTokenError(Exception):
    """Raised when websocket token validation fails."""
    pass
