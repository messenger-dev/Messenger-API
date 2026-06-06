class AppError(Exception):
    """Base class for application-specific exceptions."""


class EmailServiceError(Exception):
    """Raised when email service operations fail."""
    pass


class InvalidWebSocketTokenError(Exception):
    """Raised when websocket token validation fails."""
    pass
