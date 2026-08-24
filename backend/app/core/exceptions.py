"""
Domain exceptions — framework-agnostic.
Services raise these; the global handler in error_handlers.py converts them to HTTP.
"""


class AppError(Exception):
    """Base for all application exceptions."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """Resource does not exist or does not belong to the requesting user."""
    pass


class ConflictError(AppError):
    """Resource already exists or state conflicts with the requested operation."""
    pass


class AuthenticationError(AppError):
    """Missing, invalid, or expired credentials."""
    pass


class AuthorizationError(AppError):
    """Credentials are valid but the user lacks permission."""
    pass


class ValidationError(AppError):
    """Business-rule validation failed (not schema validation — that's Pydantic's job)."""
    pass
