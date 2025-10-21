"""Health check and monitoring endpoints."""

import logging
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.infrastructure.monitoring import get_metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Application start time
_start_time = time.time()


@router.get(
    "",
    summary="Health check",
    description="Basic health check endpoint",
)
async def health_check() -> Dict[str, Any]:
    """Basic health check.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/ready",
    summary="Readiness check",
    description="Check if application is ready to serve requests",
)
async def readiness_check() -> JSONResponse:
    """Readiness check for Kubernetes.

    Checks if all dependencies are available and ready.

    Returns:
        Readiness status
    """
    checks = {
        "api": True,  # API is running if we're here
        "cache": await _check_cache(),
        "metrics": await _check_metrics(),
    }

    all_ready = all(checks.values())

    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "ready": all_ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@router.get(
    "/live",
    summary="Liveness check",
    description="Check if application is alive",
)
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for Kubernetes.

    Simple check that the application is running.

    Returns:
        Liveness status
    """
    return {
        "alive": True,
        "uptime_seconds": time.time() - _start_time,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/status",
    summary="Detailed status",
    description="Get detailed application status and metrics",
)
async def detailed_status() -> Dict[str, Any]:
    """Detailed status endpoint.

    Returns:
        Detailed status information
    """
    uptime = time.time() - _start_time

    # Get metrics
    metrics_collector = get_metrics_collector()
    metrics_summary = metrics_collector.get_summary()

    # Get cache stats (if available)
    cache_stats = await _get_cache_stats()

    return {
        "application": {
            "name": "Autonomous Report Generator",
            "version": "1.0.0",
            "status": "running",
            "uptime_seconds": uptime,
            "uptime_formatted": _format_uptime(uptime),
        },
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics_summary,
        "cache": cache_stats,
        "components": {
            "api": "healthy",
            "ontology_parser": "healthy",
            "structure_extractor": "healthy",
            "quality_assessor": "healthy",
            "export_manager": "healthy",
            "cache": "healthy" if cache_stats.get("available") else "degraded",
            "metrics": "healthy",
        },
    }


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Get Prometheus-formatted metrics",
)
async def prometheus_metrics() -> str:
    """Export Prometheus metrics.

    Returns:
        Prometheus-formatted metrics
    """
    metrics_collector = get_metrics_collector()
    return metrics_collector.export_prometheus()


async def _check_cache() -> bool:
    """Check cache availability.

    Returns:
        True if cache is available
    """
    try:
        # Try to import and check cache
        from src.infrastructure.cache import create_default_cache_manager

        cache_manager = create_default_cache_manager()

        # Simple cache operation test
        test_key = "__health_check__"
        cache_manager.set(test_key, "test", ttl=10)
        result = cache_manager.get(test_key)
        cache_manager.delete(test_key)

        return result == "test"
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")
        return False


async def _check_metrics() -> bool:
    """Check metrics system.

    Returns:
        True if metrics are available
    """
    try:
        metrics_collector = get_metrics_collector()
        summary = metrics_collector.get_summary()
        return "total_metrics" in summary
    except Exception as e:
        logger.warning(f"Metrics check failed: {e}")
        return False


async def _get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics.

    Returns:
        Cache statistics
    """
    try:
        from src.infrastructure.cache import create_default_cache_manager

        cache_manager = create_default_cache_manager()
        stats = cache_manager.get_stats()

        return {
            "available": True,
            **stats,
        }
    except Exception as e:
        logger.warning(f"Failed to get cache stats: {e}")
        return {
            "available": False,
            "error": str(e),
        }


def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format.

    Args:
        seconds: Uptime in seconds

    Returns:
        Formatted uptime string
    """
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)
