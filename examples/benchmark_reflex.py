"""Local recall/latency microbenchmark; emits no invented agent-token savings.

Run after installing calyx-mcp: python examples/benchmark_reflex.py --samples 100
Uses synthetic code and fresh temporary memory per family, never ~/.calyx.
"""
import argparse
import asyncio
from dataclasses import asdict
import json
import platform
import statistics
import tempfile
import time

import numpy as np
from calyx_mcp.config import CalyxConfig
from calyx_mcp.server import CalyxMCPServer


FAMILIES = [
    ("literal_divisor", "def scale(x): return x / 0",
     "def normalize(value): return value / 0", "def scale(x): return x / 1",
     "x is an integer in [-1000,1000]; literal zero divisor raises"),
    ("last_index", "def last(xs): return xs[len(xs)]",
     "def tail(values): return values[len(values)]", "def last(xs): return xs[len(xs)-1]",
     "xs is a nonempty list; index equal to length is out of bounds"),
    ("mutable_default", "def collect(x, items=[]):\n    items.append(x)\n    return items",
     "def gather(value, results=[]):\n    results.append(value)\n    return results",
     "def collect(x, items=None):\n    if items is None: items = []\n    items.append(x)\n    return items",
     "repeated calls without items should not share list state"),
]


async def benchmark(samples):
    rows = []
    latencies = []
    for family, trained, renamed, fixed, contract in FAMILIES:
        with tempfile.TemporaryDirectory(prefix="calyx-benchmark-") as folder:
            cfg = CalyxConfig()
            cfg.storage.storage_dir = folder
            server = CalyxMCPServer(cfg)
            cold = await server.reflex_engine.evaluate_reflex(trained)
            assert cold.status == "neutral"
            await server.memory.remember(trained, "failure", contract)
            for kind, code, expected in (
                ("exact", trained, True), ("renamed", renamed, True),
                ("fixed", fixed, False), ("unrelated", 'def greet(name): return "Hello " + name', False),
            ):
                result = await server.reflex_engine.evaluate_reflex(code)
                rows.append({"family": family, "kind": kind, "code": code, "contract": contract,
                             "expected_bug": expected, "outcome": asdict(result)})
            for i in range(samples + 10):
                start = time.perf_counter_ns()
                await server.reflex_engine.evaluate_reflex(trained)
                elapsed = (time.perf_counter_ns() - start) / 1e6
                if i >= 10:
                    latencies.append(elapsed)
    return {"python": platform.python_version(), "numpy": np.__version__,
            "measurement": "in-process evaluate_reflex, one memory per family; excludes stdio, startup and training",
            "samples": len(latencies), "median_ms": statistics.median(latencies),
            "p95_ms": float(np.percentile(latencies, 95)), "agent_tokens_saved": None,
            "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=100)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    print(json.dumps(asyncio.run(benchmark(args.samples)), indent=2))
