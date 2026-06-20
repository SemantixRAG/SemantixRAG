"""Telemetry collection and metrics aggregation (Obsidian)."""
import logging
import time
from datetime import datetime
from typing import Optional, Any, Callable
from collections import defaultdict
from ..config.settings import settings
from ..models import CostRecord

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and aggregate telemetry metrics."""

    def __init__(self, opensearch_client=None):
        self.client = opensearch_client
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def increment(self, metric: str, value: int = 1, tags: Optional[dict] = None):
        """Increment a counter metric."""
        self._counters[metric] += value

    def gauge(self, metric: str, value: float, tags: Optional[dict] = None):
        """Set a gauge metric."""
        self._gauges[metric] = value

    def histogram(self, metric: str, value: float, tags: Optional[dict] = None):
        """Record a histogram value."""
        self._histograms[metric].append(value)

    def record_latency(self, operation: str, duration_ms: float):
        """Record operation latency."""
        self.histogram(f"{operation}.latency", duration_ms)
        if self.client:
            try:
                self.client.index(
                    index=settings.observability_index,
                    document={
                        "operation": operation,
                        "duration_ms": duration_ms,
                        "timestamp": datetime.utcnow().isoformat(),
                        "metric_type": "latency",
                    },
                )
            except Exception as e:
                logger.error(f"Failed to record latency: {e}")

    def record_cost(self, record: CostRecord):
        """Record cost for an operation."""
        if not settings.cost_tracking_enabled:
            return
        self.increment("cost.total", int(record.cost_usd * 1000))
        if self.client:
            try:
                self.client.index(
                    index=settings.observability_index,
                    document={
                        "operation": record.operation,
                        "model": record.model,
                        "tokens": record.tokens,
                        "cost_usd": record.cost_usd,
                        "tenant_id": record.tenant_id,
                        "timestamp": record.timestamp or datetime.utcnow().isoformat(),
                        "metric_type": "cost",
                    },
                )
            except Exception as e:
                logger.error(f"Failed to record cost: {e}")

    def get_counter(self, metric: str) -> int:
        return self._counters.get(metric, 0)

    def get_histogram_stats(self, metric: str) -> dict:
        values = self._histograms.get(metric, [])
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        sorted_values = sorted(values)
        n = len(sorted_values)
        return {
            "count": n,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(sorted_values) / n,
            "p50": sorted_values[int(n * 0.50)],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)],
        }

    def snapshot(self) -> dict:
        """Return current snapshot of all metrics."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: self.get_histogram_stats(k)
                for k in self._histograms
            },
        }

    def reset(self):
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, operation: str):
        self.collector = collector
        self.operation = operation
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.collector.record_latency(self.operation, duration_ms)


# Global metrics collector
metrics_collector = MetricsCollector()