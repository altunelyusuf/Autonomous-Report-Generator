"""API-specific exceptions."""

from typing import Any, Dict, Optional


class APIException(Exception):
    """Base API exception."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize API exception.

        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ReportNotFoundException(APIException):
    """Report not found exception."""

    def __init__(self, report_id: str):
        """Initialize exception."""
        super().__init__(
            message=f"Report not found: {report_id}",
            status_code=404,
            details={"report_id": report_id},
        )


class InvalidRequestException(APIException):
    """Invalid request exception."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception."""
        super().__init__(
            message=message,
            status_code=400,
            details=details,
        )


class ReportGenerationException(APIException):
    """Report generation failed exception."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception."""
        super().__init__(
            message=f"Report generation failed: {message}",
            status_code=500,
            details=details,
        )


class QualityAssessmentException(APIException):
    """Quality assessment failed exception."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception."""
        super().__init__(
            message=f"Quality assessment failed: {message}",
            status_code=500,
            details=details,
        )


class ExportException(APIException):
    """Export operation failed exception."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception."""
        super().__init__(
            message=f"Export failed: {message}",
            status_code=500,
            details=details,
        )


class ServiceUnavailableException(APIException):
    """Service unavailable exception."""

    def __init__(self, service: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception."""
        super().__init__(
            message=f"Service unavailable: {service}",
            status_code=503,
            details=details,
        )


class RateLimitException(APIException):
    """Rate limit exceeded exception."""

    def __init__(self, message: str = "Rate limit exceeded"):
        """Initialize exception."""
        super().__init__(
            message=message,
            status_code=429,
        )


class AuthenticationException(APIException):
    """Authentication failed exception."""

    def __init__(self, message: str = "Authentication required"):
        """Initialize exception."""
        super().__init__(
            message=message,
            status_code=401,
        )


class AuthorizationException(APIException):
    """Authorization failed exception."""

    def __init__(self, message: str = "Insufficient permissions"):
        """Initialize exception."""
        super().__init__(
            message=message,
            status_code=403,
        )
