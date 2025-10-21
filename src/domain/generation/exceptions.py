"""Exceptions for content generation."""


class GenerationException(Exception):
    """Base exception for generation errors."""

    pass


class ProviderException(GenerationException):
    """Exception for LLM provider errors."""

    pass


class TemplateException(GenerationException):
    """Exception for template rendering errors."""

    pass


class ValidationException(GenerationException):
    """Exception for validation errors."""

    pass


class QuotaException(GenerationException):
    """Exception for quota/rate limit errors."""

    pass
