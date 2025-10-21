"""Structured logging configuration."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    json_logs: bool = False,
) -> None:
    """Configure structured logging.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_logs: Whether to output JSON logs
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Console output for development
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Add file handler if log file specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)

        if json_logs:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        file_handler.setFormatter(formatter)
        logging.root.addHandler(file_handler)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record

        Returns:
            JSON-formatted log entry
        """
        import json

        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def get_logger(name: str, **context: Any) -> structlog.BoundLogger:
    """Get a logger with optional context.

    Args:
        name: Logger name
        **context: Additional context to bind

    Returns:
        Configured logger
    """
    logger = structlog.get_logger(name)

    if context:
        logger = logger.bind(**context)

    return logger


class RequestLogger:
    """Logger for HTTP requests.

    Logs request/response details with timing.
    """

    def __init__(self, logger_name: str = "api.requests"):
        """Initialize request logger.

        Args:
            logger_name: Logger name
        """
        self.logger = get_logger(logger_name)

    async def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        **extra: Any,
    ) -> None:
        """Log HTTP request.

        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration: Request duration in seconds
            **extra: Additional context
        """
        self.logger.info(
            "http_request",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration * 1000,
            **extra,
        )


class PerformanceLogger:
    """Logger for performance metrics."""

    def __init__(self, logger_name: str = "performance"):
        """Initialize performance logger.

        Args:
            logger_name: Logger name
        """
        self.logger = get_logger(logger_name)

    def log_operation(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        **context: Any,
    ) -> None:
        """Log operation performance.

        Args:
            operation: Operation name
            duration: Duration in seconds
            success: Whether operation succeeded
            **context: Additional context
        """
        self.logger.info(
            "operation",
            operation=operation,
            duration_ms=duration * 1000,
            success=success,
            **context,
        )


class AuditLogger:
    """Logger for audit events."""

    def __init__(self, logger_name: str = "audit"):
        """Initialize audit logger.

        Args:
            logger_name: Logger name
        """
        self.logger = get_logger(logger_name)

    def log_event(
        self,
        event_type: str,
        user: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        **context: Any,
    ) -> None:
        """Log audit event.

        Args:
            event_type: Event type
            user: User identifier
            resource: Resource identifier
            action: Action performed
            **context: Additional context
        """
        self.logger.info(
            "audit_event",
            event_type=event_type,
            user=user,
            resource=resource,
            action=action,
            **context,
        )


# Default loggers
def get_api_logger() -> structlog.BoundLogger:
    """Get API logger."""
    return get_logger("api")


def get_domain_logger() -> structlog.BoundLogger:
    """Get domain logger."""
    return get_logger("domain")


def get_infrastructure_logger() -> structlog.BoundLogger:
    """Get infrastructure logger."""
    return get_logger("infrastructure")
