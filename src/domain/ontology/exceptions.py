"""Exceptions for ontology processing."""

from typing import Optional


class OntologyException(Exception):
    """Base exception for ontology operations."""

    pass


class ParsingException(OntologyException):
    """Raised when ontology cannot be parsed."""

    def __init__(self, message: str, line_number: Optional[int] = None):
        """Initialize parsing exception.

        Args:
            message: Error message
            line_number: Optional line number where error occurred
        """
        self.line_number = line_number
        if line_number:
            super().__init__(f"{message} (line {line_number})")
        else:
            super().__init__(message)


class ValidationException(OntologyException):
    """Raised when ontology validation fails."""

    pass


class TimeoutException(OntologyException):
    """Raised when parsing exceeds timeout."""

    pass


class UnsupportedFormatException(OntologyException):
    """Raised when ontology format is not supported."""

    def __init__(self, format: str):
        """Initialize unsupported format exception.

        Args:
            format: The unsupported format
        """
        super().__init__(f"Unsupported ontology format: {format}")


class CircularInheritanceException(ValidationException):
    """Raised when circular inheritance is detected."""

    def __init__(self, class_uri: str):
        """Initialize circular inheritance exception.

        Args:
            class_uri: URI of the class with circular inheritance
        """
        super().__init__(f"Circular inheritance detected at class: {class_uri}")
