"""Metrics and monitoring utilities."""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Metric type enumeration."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Base metric class."""

    name: str
    metric_type: MetricType
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    description: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary.

        Returns:
            Metric dictionary
        """
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
            "description": self.description,
        }


@dataclass
class Counter(Metric):
    """Counter metric (monotonically increasing)."""

    metric_type: MetricType = MetricType.COUNTER

    def increment(self, value: float = 1.0) -> None:
        """Increment counter.

        Args:
            value: Value to add
        """
        self.value += value
        self.timestamp = time.time()
        logger.debug(f"Counter {self.name} incremented by {value} to {self.value}")

    def reset(self) -> None:
        """Reset counter to zero."""
        self.value = 0.0
        self.timestamp = time.time()


@dataclass
class Gauge(Metric):
    """Gauge metric (can go up or down)."""

    metric_type: MetricType = MetricType.GAUGE

    def set(self, value: float) -> None:
        """Set gauge value.

        Args:
            value: New value
        """
        self.value = value
        self.timestamp = time.time()
        logger.debug(f"Gauge {self.name} set to {value}")

    def increment(self, value: float = 1.0) -> None:
        """Increment gauge.

        Args:
            value: Value to add
        """
        self.value += value
        self.timestamp = time.time()

    def decrement(self, value: float = 1.0) -> None:
        """Decrement gauge.

        Args:
            value: Value to subtract
        """
        self.value -= value
        self.timestamp = time.time()


@dataclass
class Histogram(Metric):
    """Histogram metric (distribution of values)."""

    metric_type: MetricType = MetricType.HISTOGRAM
    observations: List[float] = field(default_factory=list)
    buckets: List[float] = field(default_factory=lambda: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0])

    def observe(self, value: float) -> None:
        """Observe a value.

        Args:
            value: Value to observe
        """
        self.observations.append(value)
        self.timestamp = time.time()
        logger.debug(f"Histogram {self.name} observed {value}")

    def get_percentile(self, percentile: float) -> float:
        """Get percentile value.

        Args:
            percentile: Percentile (0-100)

        Returns:
            Percentile value
        """
        if not self.observations:
            return 0.0

        sorted_obs = sorted(self.observations)
        index = int(len(sorted_obs) * percentile / 100)
        return sorted_obs[min(index, len(sorted_obs) - 1)]

    def get_stats(self) -> dict:
        """Get histogram statistics.

        Returns:
            Statistics dictionary
        """
        if not self.observations:
            return {
                "count": 0,
                "sum": 0.0,
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        return {
            "count": len(self.observations),
            "sum": sum(self.observations),
            "min": min(self.observations),
            "max": max(self.observations),
            "mean": sum(self.observations) / len(self.observations),
            "p50": self.get_percentile(50),
            "p95": self.get_percentile(95),
            "p99": self.get_percentile(99),
        }


@dataclass
class Timer(Histogram):
    """Timer metric (measures duration)."""

    metric_type: MetricType = MetricType.TIMER

    @contextmanager
    def time(self):
        """Context manager to time operations.

        Usage:
            with timer.time():
                # operation to time
                pass
        """
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.observe(duration)


class MetricsCollector:
    """Collect and manage metrics.

    Features:
    - Multiple metric types
    - Label-based filtering
    - Automatic aggregation
    - Export capabilities
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._metrics: Dict[str, Metric] = {}
        self._start_time = time.time()

    def counter(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Counter:
        """Get or create counter metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Metric labels

        Returns:
            Counter metric
        """
        metric_key = self._get_metric_key(name, labels)

        if metric_key not in self._metrics:
            self._metrics[metric_key] = Counter(
                name=name,
                description=description,
                labels=labels or {},
            )

        return self._metrics[metric_key]

    def gauge(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Gauge:
        """Get or create gauge metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Metric labels

        Returns:
            Gauge metric
        """
        metric_key = self._get_metric_key(name, labels)

        if metric_key not in self._metrics:
            self._metrics[metric_key] = Gauge(
                name=name,
                description=description,
                labels=labels or {},
            )

        return self._metrics[metric_key]

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> Histogram:
        """Get or create histogram metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Metric labels
            buckets: Histogram buckets

        Returns:
            Histogram metric
        """
        metric_key = self._get_metric_key(name, labels)

        if metric_key not in self._metrics:
            hist = Histogram(
                name=name,
                description=description,
                labels=labels or {},
            )
            if buckets:
                hist.buckets = buckets
            self._metrics[metric_key] = hist

        return self._metrics[metric_key]

    def timer(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Timer:
        """Get or create timer metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Metric labels

        Returns:
            Timer metric
        """
        metric_key = self._get_metric_key(name, labels)

        if metric_key not in self._metrics:
            self._metrics[metric_key] = Timer(
                name=name,
                description=description,
                labels=labels or {},
            )

        return self._metrics[metric_key]

    def get_all_metrics(self) -> List[Metric]:
        """Get all metrics.

        Returns:
            List of metrics
        """
        return list(self._metrics.values())

    def get_metrics_by_name(self, name: str) -> List[Metric]:
        """Get metrics by name.

        Args:
            name: Metric name

        Returns:
            List of matching metrics
        """
        return [m for m in self._metrics.values() if m.name == name]

    def get_metrics_by_type(self, metric_type: MetricType) -> List[Metric]:
        """Get metrics by type.

        Args:
            metric_type: Metric type

        Returns:
            List of matching metrics
        """
        return [m for m in self._metrics.values() if m.metric_type == metric_type]

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics
        """
        lines = []

        for metric in self._metrics.values():
            # Add HELP line
            if metric.description:
                lines.append(f"# HELP {metric.name} {metric.description}")

            # Add TYPE line
            lines.append(f"# TYPE {metric.name} {metric.metric_type.value}")

            # Add metric value
            labels_str = ""
            if metric.labels:
                labels_list = [f'{k}="{v}"' for k, v in metric.labels.items()]
                labels_str = "{" + ",".join(labels_list) + "}"

            if isinstance(metric, Histogram):
                stats = metric.get_stats()
                lines.append(f"{metric.name}_count{labels_str} {stats['count']}")
                lines.append(f"{metric.name}_sum{labels_str} {stats['sum']}")
            else:
                lines.append(f"{metric.name}{labels_str} {metric.value}")

        return "\n".join(lines)

    def export_json(self) -> List[dict]:
        """Export metrics as JSON.

        Returns:
            List of metric dictionaries
        """
        return [m.to_dict() for m in self._metrics.values()]

    def get_summary(self) -> dict:
        """Get metrics summary.

        Returns:
            Summary dictionary
        """
        uptime = time.time() - self._start_time

        summary = {
            "uptime_seconds": uptime,
            "total_metrics": len(self._metrics),
            "counters": len(self.get_metrics_by_type(MetricType.COUNTER)),
            "gauges": len(self.get_metrics_by_type(MetricType.GAUGE)),
            "histograms": len(self.get_metrics_by_type(MetricType.HISTOGRAM)),
            "timers": len(self.get_metrics_by_type(MetricType.TIMER)),
        }

        return summary

    def _get_metric_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Get unique metric key.

        Args:
            name: Metric name
            labels: Metric labels

        Returns:
            Unique key
        """
        if not labels:
            return name

        labels_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{labels_str}}}"

    def clear(self) -> None:
        """Clear all metrics."""
        self._metrics.clear()
        self._start_time = time.time()


# Global metrics collector
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector.

    Returns:
        Metrics collector instance
    """
    return _metrics_collector


# Convenience functions
def counter(
    name: str, description: str = "", labels: Optional[Dict[str, str]] = None
) -> Counter:
    """Get or create counter metric."""
    return _metrics_collector.counter(name, description, labels)


def gauge(
    name: str, description: str = "", labels: Optional[Dict[str, str]] = None
) -> Gauge:
    """Get or create gauge metric."""
    return _metrics_collector.gauge(name, description, labels)


def histogram(
    name: str,
    description: str = "",
    labels: Optional[Dict[str, str]] = None,
    buckets: Optional[List[float]] = None,
) -> Histogram:
    """Get or create histogram metric."""
    return _metrics_collector.histogram(name, description, labels, buckets)


def timer(
    name: str, description: str = "", labels: Optional[Dict[str, str]] = None
) -> Timer:
    """Get or create timer metric."""
    return _metrics_collector.timer(name, description, labels)
