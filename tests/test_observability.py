"""Tests for Obsidian observability."""
import pytest
from semantixrag.observability.tracer import Tracer, TraceSpan
from semantixrag.observability.evaluator import RAGEvaluator
from semantixrag.observability.metrics import MetricsCollector, TimerContext


@pytest.fixture
def tracer():
    return Tracer()


@pytest.fixture
def evaluator():
    return RAGEvaluator()


@pytest.fixture
def collector():
    return MetricsCollector()


def test_span_lifecycle(tracer):
    span = tracer.start_span("test.operation")
    span.set_metadata("key", "value")
    span.set_tag("test")
    span.set_status("success")
    tracer.finish_span(span)
    assert span.duration_ms >= 0


def test_span_context_manager(tracer):
    with tracer.span("test.ops", custom="data") as span:
        span.set_metadata("inner", "metadata")
        assert span.status == "success"
    assert span.end_time is not None


def test_trace_hierarchy(tracer):
    parent = tracer.start_span("parent")
    child = tracer.start_span("child", parent_span_id=parent.span_id)
    tracer.finish_span(child)
    tracer.finish_span(parent)
    assert child.parent_span_id == parent.span_id


def test_span_metadata(tracer):
    span = tracer.start_span("test")
    span.set_metadata("doc_id", "1234")
    assert span.metadata["doc_id"] == "1234"


def test_span_properties():
    span = TraceSpan("trace1", "span1", "test.op")
    span.set_status("success")
    span.finish()
    assert span.status == "success"
    assert span.duration_ms >= 0


def test_span_error(tracer):
    with pytest.raises(ValueError):
        with tracer.span("failing.op"):
            raise ValueError("Test error")
    assert tracer._spans
    for span in tracer._spans.values():
        assert span.status in ("success", "error")


class TestRAGEvaluator:
    @pytest.mark.asyncio
    async def test_faithfulness(self, evaluator):
        score = await evaluator.evaluate_faithfulness(
            "Apple revenue grew 23%",
            ["Apple revenue grew 23% in Q3"],
        )
        assert 0 <= score <= 1
        assert score > 0.5

    @pytest.mark.asyncio
    async def test_faithfulness_no_context(self, evaluator):
        score = await evaluator.evaluate_faithfulness("Answer", [])
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_answer_relevancy(self, evaluator):
        score = await evaluator.evaluate_answer_relevancy(
            "What is revenue growth?",
            "Revenue growth was 23%",
        )
        assert 0 <= score <= 1

    def test_mrr(self, evaluator):
        mrr = evaluator.compute_mrr(
            ["doc1", "doc2", "doc3"],
            {"doc2"},
        )
        assert mrr == 0.5

    def test_recall_at_k(self, evaluator):
        recall = evaluator.compute_recall_at_k(
            ["doc1", "doc2", "doc3"],
            {"doc2", "doc4"},
            k=2,
        )
        assert recall == 0.5

    def test_precision_at_k(self, evaluator):
        precision = evaluator.compute_precision_at_k(
            ["doc1", "doc2", "doc3"],
            {"doc2"},
            k=2,
        )
        assert precision == 0.5

    @pytest.mark.asyncio
    async def test_groundedness(self, evaluator):
        result = await evaluator.evaluate_groundedness(
            "Revenue grew 23%",
            ["Revenue grew 23%"],
        )
        assert "faithfulness" in result
        assert "overall_groundedness" in result


class TestMetricsCollector:
    def test_counter(self, collector):
        collector.increment("test.count")
        assert collector.get_counter("test.count") == 1

    def test_counter_multiple(self, collector):
        collector.increment("test.count", 5)
        assert collector.get_counter("test.count") == 5

    def test_gauge(self, collector):
        collector.gauge("test.gauge", 42.5)
        stats = collector.snapshot()
        assert stats["gauges"]["test.gauge"] == 42.5

    def test_histogram(self, collector):
        collector.histogram("test.latency", 100)
        collector.histogram("test.latency", 200)
        stats = collector.get_histogram_stats("test.latency")
        assert stats["count"] == 2
        assert stats["min"] == 100
        assert stats["max"] == 200

    def test_empty_histogram(self, collector):
        stats = collector.get_histogram_stats("nonexistent")
        assert stats["count"] == 0

    def test_snapshot(self, collector):
        collector.increment("req.count", 10)
        collector.gauge("cpu.pct", 75.0)
        snapshot = collector.snapshot()
        assert "counters" in snapshot
        assert "gauges" in snapshot
        assert "histograms" in snapshot

    def test_reset(self, collector):
        collector.increment("test")
        collector.reset()
        assert collector.get_counter("test") == 0

    def test_timer_context(self, collector):
        with TimerContext(collector, "test.op"):
            pass
        stats = collector.get_histogram_stats("test.op.latency")
        assert stats["count"] == 1


@pytest.mark.asyncio
async def test_cost_record(collector):
    from src.models import CostRecord
    record = CostRecord(
        operation="embedding",
        model="bge-m3",
        tokens=1000,
        cost_usd=0.01,
        tenant_id="default",
    )
    collector.record_cost(record)
    assert collector.get_counter("cost.total") >= 10