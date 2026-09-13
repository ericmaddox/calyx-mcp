"""The changed-code control must reject blindly repeated classifications."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    "benchmark_continuations", Path(__file__).resolve().parents[2] / "examples" / "benchmark_continuations.py"
)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def test_fixture_contracts_reverse_all_four_classifications():
    initial = benchmark.expected_results(benchmark.INITIAL)
    changed = benchmark.expected_results(benchmark.CHANGED)
    assert initial == {"A": True, "B": False, "C": True, "D": False}
    assert changed == {"A": False, "B": True, "C": False, "D": True}
    repeated = {"results": [{"id": key, "bug": value} for key, value in initial.items()]}
    assert benchmark.accepted(repeated, initial)
    assert not benchmark.accepted(repeated, changed)


def test_acceptance_rejects_missing_duplicate_and_non_boolean_answers():
    expected = benchmark.expected_results(benchmark.INITIAL)
    assert not benchmark.accepted({}, expected)
    assert not benchmark.accepted({"results": [{"id": "A", "bug": True}] * 4}, expected)
    assert not benchmark.accepted({"results": [{"id": key, "bug": int(value)} for key, value in expected.items()]}, expected)


def test_deltas_match_observed_resumed_usage_and_fail_on_reset():
    first = {"input_tokens": 17869, "output_tokens": 109, "cached_input_tokens": 0, "reasoning_output_tokens": 0}
    second = {"input_tokens": 35856, "output_tokens": 218, "cached_input_tokens": 17664, "reasoning_output_tokens": 0}
    assert benchmark.cumulative_delta(second, first) == {
        "input_tokens": 17987, "output_tokens": 109, "cached_input_tokens": 17664, "reasoning_output_tokens": 0,
    }
    with pytest.raises(ValueError):
        benchmark.cumulative_delta(first, second)
