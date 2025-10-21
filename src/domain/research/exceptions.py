"""Exceptions for research operations."""

from typing import Optional


class ResearchException(Exception):
    """Base exception for research operations."""

    pass


class SearchException(ResearchException):
    """Raised when search operation fails."""

    def __init__(self, message: str, source: Optional[str] = None):
        """Initialize search exception.

        Args:
            message: Error message
            source: Optional source name
        """
        self.source = source
        if source:
            super().__init__(f"{source}: {message}")
        else:
            super().__init__(message)


class ValidationException(ResearchException):
    """Raised when query validation fails."""

    pass


class TimeoutException(ResearchException):
    """Raised when research operation times out."""

    pass


class RateLimitException(ResearchException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        """Initialize rate limit exception.

        Args:
            message: Error message
            retry_after: Seconds until retry is allowed
        """
        self.retry_after = retry_after
        super().__init__(message)


class AuthenticationException(ResearchException):
    """Raised when authentication fails."""

    pass


class SourceUnavailableException(ResearchException):
    """Raised when a research source is unavailable."""

    def __init__(self, source: str, message: Optional[str] = None):
        """Initialize source unavailable exception.

        Args:
            source: Source name
            message: Optional error message
        """
        self.source = source
        msg = f"Source '{source}' is unavailable"
        if message:
            msg += f": {message}"
        super().__init__(msg)
