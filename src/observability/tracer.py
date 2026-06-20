"""AI-native observability instrumentation (Obsidian)."""
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Optional, Dict, Any
from ..config.settings import settings

logger = logging.getLogger(__name__)


class TraceSpan:
    """Represents a single trace span."""

    def __init__(
        self,
        trace_id: str,
        span_id: str,
        operation: str,
        parent_span_id: Optional[str] = None,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.operation = operation
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.status = "success"
        self.metadata: Dict[str, Any] = {}
        self.tags: list[str] = []

    def set_status(self, status: str):
        self.status = status

    def set_metadata(self, key: str, value: Any):
        self.metadata[key] = value

    def set_tag(self, tag: str):
        self.tags.append(tag)

    def finish(self):
        self.end_time = time.time()

    @property
    def duration_ms(self) -> int:
        if self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0


class Tracer:
    """Core tracing client for Obsidian observability."""

    def __init__(self, opensearch_client=None):
        self.client = opensearch_client
        self._spans: Dict[str, TraceSpan] = {}
        self._sample_rate = settings.observability_sample_rate

    def start_span(
        self,
        operation: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> TraceSpan:
        """Start a new trace span."""
        trace_id = trace_id or str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        span = TraceSpan(trace_id, span_id, operation, parent_span_id)
        self._spans[span_id] = span
        return span

    def finish_span(self, span: TraceSpan):
        """Finish a trace span and emit to telemetry store."""
        span.finish()
        self._emit(span)

    @contextmanager
    def span(self, operation: str, trace_id: Optional[str] = None, **metadata):
        """Context manager for automatic instrumentation."""
        span = self.start_span(operation, trace_id)
        span.set_metadata("operation", operation)
        for k, v in metadata.items():
            span.set_metadata(k, v)
        try:
            yield span
            span.set_status("success")
        except Exception as e:
            span.set_status("error")
            span.set_metadata("error", str(e))
            raise
        finally:
            self.finish_span(span)

    def _emit(self, span: TraceSpan):
        """Emit span to telemetry store."""
        if not settings.observability_enabled:
            return

        if hash(span.trace_id) % 100 > int(self._sample_rate * 100):
            return

        document = {
            "trace_id": span.trace_id,
            "parent_trace_id": span.parent_span_id,
            "span_id": span.span_id,
            "operation": span.operation,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "duration_ms": span.duration_ms,
            "status": span.status,
            "metadata": span.metadata,
            "tags": span.tags,
        }

        try:
            if self.client:
                self.client.index(
                    index=settings.observability_index,
                    document=document,
                )
        except Exception as e:
            logger.error(f"Failed to emit trace: {e}")

    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        return self._spans.get(span_id)

    def clear(self):
        """Clear completed spans (call after batch)."""
        self._spans.clear()


# Global tracer instance
tracer = Tracer()