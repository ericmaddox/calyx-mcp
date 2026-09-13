import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "benchmark_learned_reuse", Path(__file__).resolve().parents[2] / "examples" / "benchmark_learned_reuse.py"
)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def test_accepts_the_verified_fix_and_rejects_the_bug():
    assert benchmark.validate_patch("def cache_key(symbol, venue): return (venue, symbol)", benchmark.TRAINED)
    assert not benchmark.validate_patch(benchmark.TRAINED)
    assert not benchmark.validate_patch("def cache_key(symbol, venue): return (symbol, venue)")
    assert not benchmark.validate_patch("def wrong(symbol, venue): return (venue, symbol)", benchmark.TRAINED)


@pytest.mark.parametrize("code", [
    "import os", "def f(a,b): return eval(a)",
    "def f(a,b): return a.__class__", "@evil\ndef f(a,b): return (b,a)",
    "def f(a,b):\n while True: pass", "def f(a,b): return [b,a]",
])
def test_rejects_non_pure_generated_code_without_executing_it(code):
    assert not benchmark.validate_patch(code)
