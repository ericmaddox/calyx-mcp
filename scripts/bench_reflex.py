#!/usr/bin/env python3
"""
Benchmark harness for Calyx MCP Reflex Decision Engine.
Accurately measures latency across:
  1. Real-path check_code_reflex (including MCP tool validation, shared storage reload, and matrix math)
  2. In-memory-only reflex evaluation (historical baseline)
Runs 1,000 iterations and computes p50, p90, p95, p99, and throughput.
"""

import sys
import os
import json
import time
import asyncio
import tempfile
from pathlib import Path
import numpy as np

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from calyx_mcp.config import CalyxConfig
from calyx_mcp.server import CalyxMCPServer


BENCHMARK_SNIPPETS = [
    "def query_user(cursor, username):\n    query = f\"SELECT * FROM users WHERE username = '{username}'\"\n    cursor.execute(query)\n    return cursor.fetchone()\n",
    "def read_all_logs(log_paths):\n    data = []\n    for path in log_paths:\n        with open(path, 'r') as f:\n            data.append(f.read())\n    return data\n",
    "def wait_for_ready(queue):\n    while True:\n        item = queue.poll()\n        if item is not None:\n            return item\n        time.sleep(0.01)\n",
    "async function fetchUser(client, id) {\n    return await client.query('SELECT * FROM users WHERE id = $1', [id]);\n}\n",
    "fn compute_hash(data: &[u8]) -> Vec<u8> {\n    let mut hasher = Sha256::new();\n    hasher.update(data);\n    hasher.finalize().to_vec()\n}\n",
]


async def run_benchmark(num_calls: int = 1000, output_path: Path = None):
    print("=" * 80)
    print("CALYX MCP REFLEX ENGINE REAL-WORLD LATENCY BENCHMARK")
    print(f"Total Iterations: {num_calls}")
    print("=" * 80)

    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg = CalyxConfig()
        cfg.storage.storage_dir = tmp_dir
        server = CalyxMCPServer(cfg)

        # Pre-populate memory with realistic history (10 failures, 20 successes)
        print("Pre-populating memory state with 30 records...")
        for i, snippet in enumerate(BENCHMARK_SNIPPETS):
            await server.execute_tool(
                "remember_code_outcome",
                {"code": snippet, "outcome": "failure", "error_message": f"Historical bug #{i}"}
            )
            await server.execute_tool(
                "remember_code_outcome",
                {"code": snippet + f"\n# fix {i}", "outcome": "success"}
            )
            await server.execute_tool(
                "remember_code_outcome",
                {"code": snippet + f"\n# verified {i}", "outcome": "success"}
            )

        # ---------------------------------------------------------
        # Benchmark 1: Real-path check_code_reflex (MCP tool + snapshot refresh)
        # ---------------------------------------------------------
        print(f"\nRunning Benchmark 1: Real-Path check_code_reflex ({num_calls} calls)...")
        real_latencies = []
        for i in range(num_calls):
            snippet = BENCHMARK_SNIPPETS[i % len(BENCHMARK_SNIPPETS)]
            t0 = time.perf_counter()
            await server.execute_tool("check_code_reflex", {"code": snippet})
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            real_latencies.append(elapsed_ms)

        # ---------------------------------------------------------
        # Benchmark 2: In-memory-only evaluation (direct reflex engine call)
        # ---------------------------------------------------------
        print(f"Running Benchmark 2: In-Memory-Only evaluation ({num_calls} calls)...")
        in_memory_latencies = []
        for i in range(num_calls):
            snippet = BENCHMARK_SNIPPETS[i % len(BENCHMARK_SNIPPETS)]
            t0 = time.perf_counter()
            # Direct matrix evaluation on existing in-memory snapshot
            rep = server.memory.hasher.hash_code(snippet)
            active_weights = server.memory.weights[rep.active_indices]
            _ = float(np.mean(active_weights))
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            in_memory_latencies.append(elapsed_ms)

        # Statistical calculations
        real_p50 = float(np.percentile(real_latencies, 50))
        real_p90 = float(np.percentile(real_latencies, 90))
        real_p95 = float(np.percentile(real_latencies, 95))
        real_p99 = float(np.percentile(real_latencies, 99))
        real_mean = float(np.mean(real_latencies))
        real_throughput = 1000.0 / real_mean if real_mean > 0 else 0.0

        mem_p50 = float(np.percentile(in_memory_latencies, 50))
        mem_p90 = float(np.percentile(in_memory_latencies, 90))
        mem_p95 = float(np.percentile(in_memory_latencies, 95))
        mem_p99 = float(np.percentile(in_memory_latencies, 99))
        mem_mean = float(np.mean(in_memory_latencies))
        mem_throughput = 1000.0 / mem_mean if mem_mean > 0 else 0.0

        print("\n" + "=" * 80)
        print("LATENCY RESULTS (1,000 iterations)")
        print("=" * 80)
        print(f"{'Metric':<25} | {'In-Memory (Historical)':<24} | {'Real-Path (End-to-End)':<24}")
        print("-" * 80)
        print(f"{'p50 (Median)':<25} | {mem_p50:.4f} ms{'':<15} | {real_p50:.4f} ms")
        print(f"{'Mean':<25} | {mem_mean:.4f} ms{'':<15} | {real_mean:.4f} ms")
        print(f"{'p90':<25} | {mem_p90:.4f} ms{'':<15} | {real_p90:.4f} ms")
        print(f"{'p95':<25} | {mem_p95:.4f} ms{'':<15} | {real_p95:.4f} ms")
        print(f"{'p99':<25} | {mem_p99:.4f} ms{'':<15} | {real_p99:.4f} ms")
        print(f"{'Throughput':<25} | {mem_throughput:.0f} req/s{'':<14} | {real_throughput:.0f} req/s")
        print("=" * 80)

        results = {
            "num_calls": num_calls,
            "real_path": {
                "mean_ms": real_mean,
                "p50_ms": real_p50,
                "p90_ms": real_p90,
                "p95_ms": real_p95,
                "p99_ms": real_p99,
                "throughput_rps": real_throughput,
            },
            "in_memory_only": {
                "mean_ms": mem_mean,
                "p50_ms": mem_p50,
                "p90_ms": mem_p90,
                "p95_ms": mem_p95,
                "p99_ms": mem_p99,
                "throughput_rps": mem_throughput,
            }
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"Saved benchmark results to {output_path}")

        return results


def main():
    output_path = Path("benchmarks/2026-09-eval/latency_benchmark.json")
    asyncio.run(run_benchmark(num_calls=1000, output_path=output_path))


if __name__ == "__main__":
    main()
