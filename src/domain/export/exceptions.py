"""Exceptions for export operations."""


class ExportException(Exception):
    """Base exception for export errors."""

    pass


class UnsupportedFormatException(ExportException):
    """Exception for unsupported export format."""

    pass


class ExportValidationException(ExportException):
    """Exception for export validation errors."""

    pass


class TemplateException(ExportException):
    """Exception for template errors."""

    pass


class FileWriteException(ExportException):
    """Exception for file write errors."""

    pass
