"""Prevent plausible-looking savings when telemetry or acceptance is missing."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "compare_agent_usage", Path(__file__).resolve().parents[2] / "examples" / "compare_agent_usage.py"
)
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def usage(input_tokens, output_tokens, cached=0):
    return {"type": "turn.completed", "usage": {
        "input_tokens": input_tokens, "output_tokens": output_tokens, "cached_input_tokens": cached,
        "reasoning_output_tokens": 2,
    }}


def call(status="completed", error=None):
    return {"type": "item.completed", "item": {
        "type": "mcp_tool_call", "tool": "check_code_reflex", "status": status, "error": error,
    }}


def test_counts_replay_and_preserves_negative_savings_without_double_counting_cache():
    off = metrics.summarize([usage(100, 10, 80)])
    on = metrics.summarize([usage(100, 10, 80), call(), usage(120, 10, 100)])
    result = metrics.compare(off, on, True, True)
    assert result["saved_tokens"] == -130
    assert on["cached_input_tokens"] == 180
    assert result["saved_percent"] == pytest.approx(-118.181818)


@pytest.mark.parametrize("events", [
    [], [{"type": "turn.completed", "usage": {}}],
    [usage(100, 10), {"type": "turn.failed"}],
    [{"type": "turn.started"}, usage(100, 10), {"type": "turn.started"}],
    [usage(100, 10), call("failed", {"message": "approval required"})],
    [usage(-1, 10)], [usage(True, 10)],
])
def test_incomplete_failed_and_malformed_runs_cannot_claim_savings(events):
    off = metrics.summarize([usage(200, 10)])
    on = metrics.summarize(events)
    assert metrics.compare(off, on, True, True)["saved_tokens"] is None


def test_requires_acceptance_and_actual_tool_use():
    off = metrics.summarize([usage(200, 10)])
    on = metrics.summarize([usage(100, 10), call()])
    assert metrics.compare(off, on)["saved_tokens"] is None
    assert metrics.compare(off, on, True, True, expected_calls=2)["saved_tokens"] is None
    assert metrics.compare(off, on, True, True)["saved_tokens"] == 100


def test_missing_cache_telemetry_remains_unknown():
    assert metrics.summarize([{"type": "turn.completed", "usage": {
        "input_tokens": 100, "output_tokens": 10,
    }}])["cached_input_tokens"] is None


def test_resumed_session_counters_are_not_summed_in_cumulative_mode():
    result = metrics.summarize([usage(100, 10), usage(220, 20, 100)], cumulative=True)
    assert result["input_tokens"] == 220
    assert result["output_tokens"] == 20
    assert result["completed_turns"] == 2
    with pytest.raises(ValueError):
        metrics.summarize([usage(220, 20), usage(100, 10)], cumulative=True)
