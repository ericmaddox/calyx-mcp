<p align="center">
  <img src="https://raw.githubusercontent.com/ericmaddox/calyx-mcp/main/assets/calyx_banner.jpg" alt="Calyx MCP - Bio-Inspired Code Reflex Engine" width="100%" />
</p>

# Calyx MCP

[![PyPI - Version](https://img.shields.io/pypi/v/calyx-mcp?logo=pypi&logoColor=white&color=blue)](https://pypi.org/project/calyx-mcp/)
[![PyPI - Status](https://img.shields.io/pypi/status/calyx-mcp?color=blue)](https://pypi.org/project/calyx-mcp/)
[![GitHub Release](https://img.shields.io/github/v/release/ericmaddox/calyx-mcp?color=blue&logo=github)](https://github.com/ericmaddox/calyx-mcp/releases)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-59%20passed-brightgreen.svg)](tests/)
[![Latency](https://img.shields.io/badge/reflex%20latency-%3C0.5ms-success.svg)](#benchmark-and-token-savings)

Bio-inspired associative memory and instant code reflex server for AI coding agents, implementing the Drosophila Mushroom Body circuit and Fly-LSH sparse projection algorithm over the Model Context Protocol (MCP).

---

## At a Glance

* **The Problem**: AI coding agents repeatedly consume thousands of LLM prompt tokens and multi-second roundtrip latency diagnosing recurring bugs, antipatterns, and project constraints.
* **The Solution**: Calyx brings the Drosophila Mushroom Body (fruit fly brain) circuit to AI agents—using Fly-LSH sparse Kenyon Cell projection ($D=2048, k=102$) and dopaminergic synaptic plasticity to give agents instant, zero-overhead associative memory without internal LLM calls.
* **The Proof (Benchmark)**:
  * **Latency**: **0.400 ms** (vs ~1,450 ms LLM API roundtrip — **>3,600x faster**)
  * **Token Cost**: **0 tokens** (100% local Mushroom Body execution; zero LLM inference calls)

---

## Why "Calyx"?

In insect neuroanatomy, the **Calyx** (plural: *calyces*) is the primary input neuropil of the **Mushroom Body** (*Corpora Pedunculata*)—the learning and memory center of the *Drosophila melanogaster* brain. Within the calyx, olfactory and sensory Projection Neurons (PNs) synapse directly onto the clawed dendritic arborizations of thousands of Kenyon Cells (KCs).

It is inside the calyx that dense, low-dimensional sensory signals undergo high-dimensional sparse expansion, turning raw input into a distinct neural fingerprint that dopaminergic circuits can reinforce or suppress.

The name **Calyx** was chosen because this MCP server functions as that exact input and associative expansion layer for AI coding agents: converting raw code AST tokens into high-dimensional, ultra-sparse Kenyon Cell representations that drive instantaneous (<0.5 ms) reflexes, pattern recognition, and persistent synaptic memory without LLM inference costs.

---

## Overview

Traditional AI coding workflows incur substantial token overhead and multi-second latency by repeatedly sending multi-thousand-token prompt context to Large Language Models (LLMs) to detect recurring bugs, antipatterns, or architectural guidelines.

Calyx provides local, zero-token associative memory modeled after the *Drosophila melanogaster* (fruit fly) Mushroom Body circuit. Code snippets and AST structures are expanded into high-dimensional, ultra-sparse Kenyon Cell representations ($D=2048, k=102$). Synaptic plasticity between Kenyon Cells and Mushroom Body Output Neurons (MBONs) is modulated by reward and punishment signals (dopamine), delivering sub-millisecond pattern recognition without LLM inference costs.

---

## Architectural Principles

```
+-----------------------------------------------------------------------+
|                             Calyx MCP                                 |
+-----------------------------------------------------------------------+
|  Input Code Snippet / AST Tokens                                      |
|       |                                                               |
|       v                                                               |
|  Fly-LSH Hash Projection (Projection Dimension = 2048)                |
|       |                                                               |
|       v                                                               |
|  Winner-Take-All Sparsification (k = 102 active Kenyon Cells, ~5%)    |
|       |                                                               |
|       v                                                               |
|  Mushroom Body Output Neuron (MBON) Synaptic Weight Matrix            |
|       |                                                               |
|  +----+------------------------------------------------------------+  |
|  | Dopaminergic Modulation: dW = eta * Dopamine * (KC (x) MBON)    |  |
|  +-----------------------------------------------------------------+  |
|       |                                                               |
|       v                                                               |
|  Reflex Output: Neutral / Attraction / Aversion (< 0.5 ms, 0 Tokens)  |
+-----------------------------------------------------------------------+
```

1. **Fly-LSH Projection**: Projects token distributions into a 2,048-dimensional space using deterministic hashing, mimicking the projection neuron to Kenyon cell expansion.
2. **Winner-Take-All (WTA) Sparsity**: Retains only the top $k=102$ activations (~4.98% sparsity) via inhibitory feedback (APL neuron equivalent).
3. **Dopamine Synaptic Plasticity**: Adjusts synaptic weights based on coding execution outcomes (success/failure), enabling rapid aversion to bug patterns and attraction to proven implementations.
4. **Local Atomic Persistence**: Synaptic states and associative memory records persist locally in compressed `.npz` and JSON formats (`~/.calyx/`).

---

## Benchmark and Token Savings

An [actual v1.0.5 agent-usage pilot](docs/token-trial-v105.md) records six fresh
Luna sessions against 100 synthetic lessons. Only one pair met the retrieval
protocol in both arms; it used 43,591 more tokens with Calyx. Failed attempts are
retained. This bounded pilot does not demonstrate end-to-end token savings;
zero internal LLM calls and agent usage are different measurements.

The performance metrics below were measured on a Windows x86_64 host running Python 3.13 with native NumPy operations. Because Fly-LSH sparse projection and synaptic valence calculations execute locally in memory, pattern recognition requires zero external LLM inference calls:

### Test Execution Log

```text
============================================================================
        CALYX MCP: LIVE TOOL EXECUTION & TOKEN SAVINGS BENCHMARK
============================================================================

[Step 1] Initial Code Reflex Check (Zero Prior Training):
  * Latency:            0.729 ms
  * Reflex Status:      NEUTRAL
  * Valence:            1.000
  * Recommendation:     Novel or unverified code pattern. Proceed normally.
  * LLM Tokens Used:    0 tokens (Zero API overhead)

[Step 2] Dopamine Reinforcement (Negative Dopamine Delivery):
  * Plasticity Latency: 4.040 ms
  * Status:             recorded
  * Valence Type:       punishment (Dopaminergic depression signal)
  * Active Synapses:    102 Kenyon Cells updated
  * Persistent State:   Saved to ~/.calyx/mushroom_body_weights.npz

[Step 3] Fast Bio-Reflex on Novel Code Variant:
  * Latency:            0.400 ms
  * Reflex Status:      AVOID (AVERSION TRIGGERED)
  * Valence Score:      0.775 (Aversive)
  * Bug Similarity:     100.0%
  * Warning:            High resemblance (100%) to a previously punished bug pattern.
  * Recommendation:     Review code logic, check edge cases, or adopt alternative.

============================================================================
                      TOKEN SAVINGS & SPEEDUP
============================================================================
Traditional LLM Querying Loop:
  * Latency per review: ~1450 ms
  * Inspection Cost:    ~650 prompt tokens per check
  * Debugging Loop:     ~2400 tokens per repeated bug

Calyx Mushroom Body Reflex:
  * Latency per review: 0.400 ms (~3,628x speedup)
  * Token Cost:         0 tokens (Local Fly-LSH sparse projection)
  * Token Efficiency:   100% local execution (Zero LLM inference overhead)

============================================================================
              MUSHROOM BODY NEURAL ARCHITECTURE STATE
============================================================================
  * Kenyon Cells Dimension:  2048
  * Sparsity Active Ratio:   4.98% active neurons
  * Total Memories Stored:   1
  * Depressed Synapses (W):  102
  * Weights Min / Avg / Max: 0.775 / 0.9888 / 1.0
  * Storage Directory:       C:\Users\EricM\.calyx
============================================================================
```

### Performance Summary

| Metric | Traditional LLM Inspection | Calyx Mushroom Body | Improvement |
| :--- | :--- | :--- | :--- |
| **Latency** | ~1,450 ms | **0.400 ms** | **3,628x faster** |
| **Token Consumption** | 650 - 2,400 tokens per loop | **0 tokens** (Local Fly-LSH) | **100% local execution** (Zero LLM calls) |
| **Memory Footprint** | External API | **< 15 MB RAM** | Local execution |
| **Pattern Match Type** | Full prompt parsing | **Sparse Kenyon Cell overlap** | Deterministic associative recall |

---

### Real-World Bug & Vulnerability Verification

Calyx was benchmarked against real-world vulnerability and resource management patterns to test generalization across altered variable names, structural shifts, and function signatures:

| Scenario | Anti-Pattern Trained | Novel Variant Evaluated | Reflex Outcome | Latency | Tokens |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **SQL Injection (CWE-89)** | `f"SELECT ... WHERE user = '{name}'"` | Concatenation in `authenticate_admin()` | **AVOID** (Valence: 0.775) | 0.630 ms | **0 tokens** |
| **Resource Descriptor Leak** | `open()` in loop without context manager | `socket.create_connection()` unclosed | **AVOID** (Valence: 0.550) | 0.662 ms | **0 tokens** |
| **CPU Spinlock Lockup** | `while True: poll()` without delay | Unbounded message loop polling | **AVOID** (Valence: 0.775) | 0.400 ms | **0 tokens** |

## MCP Tools Reference

Calyx registers the following tools conforming to the MCP JSON-RPC 2.0 specification (2024-11-05):

### 1. `check_code_reflex`
Evaluates a code snippet against synaptic valence weights and stored experiences in <0.5ms with 0 LLM prompt tokens.
- **Annotations**: `readOnlyHint: true`, `openWorldHint: false`
- **Parameters**:
  - `code` (string, required): The proposed code snippet, function, or diff to evaluate.
  - `context` (string, optional): Optional context or filename describing the task.
- **Returns**: `status` (`avoid`, `safe`, `neutral`), `valence`, `confidence`, `similarity_with_past_bugs`, `warning`, `recommendation`.

### 2. `remember_code_outcome`
Applies one-shot dopamine reward (test passed) or punishment (test failed/bug) to Mushroom Body synaptic weights.
- **Annotations**: `readOnlyHint: false`, `destructiveHint: true`, `idempotentHint: false`, `openWorldHint: false`
- **Parameters**:
  - `code` (string, required): The code snippet that was executed or tested.
  - `outcome` (string, required): `"success"` (rewards synapses) or `"failure"` (punishes synapses).
  - `error_message` (string, optional): Error trace or description if outcome was `"failure"`.
  - `tags` (array of strings, optional): Categorical tags (e.g. `["auth", "database", "deadlock"]`).
- **Returns**: `status`, `outcome`, `valence_type`, `pattern_valence`, `active_synapses_updated`, `total_memories_stored`.

### 3. `query_associative_memory`
Searches stored code patterns using Fly-LSH sparse binary Hamming similarity.
- **Annotations**: `readOnlyHint: true`, `openWorldHint: false`
- **Parameters**:
  - `query_code` (string, required): Code snippet to search against associative memory.
  - `top_k` (integer, optional): Number of nearest neighbors to return (default: `5`, clamped $[1, 50]$).
- **Returns**: `query`, `matches_count`, `matches` (array of nearest records with similarity scores).

### 4. `inspect_memory_state`
Returns operational metrics, weight distribution, and health statistics of the Mushroom Body.
- **Annotations**: `readOnlyHint: true`, `openWorldHint: false`
- **Parameters**: None.
- **Returns**: `total_memories_stored`, `total_kenyon_cells`, `active_sparsity_pct`, `weights_avg`, `weights_min`, `weights_max`, `depressed_synapses_count`, `potentiated_synapses_count`, `storage_location`.

### 5. `reset_memory`
Resets synaptic weights to neutral baseline (1.0) and purges stored experiences with automatic backup creation.
- **Annotations**: `readOnlyHint: false`, `destructiveHint: true`, `idempotentHint: false`, `openWorldHint: false`
- **Parameters**:
  - `confirm` (boolean, required): Must be set to `true` to confirm reset.
  - `backup` (boolean, optional): Whether to create a backup file before resetting (default: `true`).
- **Returns**: `status`, `backup_created`, `backup_path`.

---

## Installation

### Option 1: Standard Installation via pip or uv (Recommended)

```bash
# Using pip
pip install calyx-mcp

# Using uv
uv pip install calyx-mcp
```

### Option 2: Run Without Installation via uvx

You can run Calyx MCP instantly without installing it into a local environment using `uvx`:

```bash
uvx calyx-mcp
```

### Option 3: Development Mode (from source)

```bash
git clone https://github.com/ericmaddox/calyx-mcp.git
cd calyx-mcp
pip install -e .
```

---

## Configuration

Add Calyx to your MCP client configuration file (e.g. `~/.gemini/config/mcp_config.json`, Claude Desktop, or Cursor):

### Using uvx (Zero-Install, Recommended)

```json
{
  "mcpServers": {
    "calyx": {
      "command": "uvx",
      "args": ["calyx-mcp"]
    }
  }
}
```

### Using Installed Python / CLI Command

```json
{
  "mcpServers": {
    "calyx": {
      "command": "calyx-mcp"
    }
  }
}
```

---

## Running Tests

Execute the 59-test suite:

```bash
python -m pytest tests/ -v
```

### Test Suite Results (59 / 59 Passing)

| Test Suite | Scope & Invariants Tested | Test Count | Status |
| :--- | :--- | :---: | :---: |
| **`tests/unit/test_contradiction_resolution.py`** | Failure Override Rule (recent failure overrides positive history), recency tie-breaking, state transitions | 3 | **PASSED** |
| **`tests/unit/test_edge_cases_and_resilience.py`** | Empty/whitespace rejection, 150KB code blocks, polyglot resilience (Rust, TypeScript, Go, SQL, JSON), unicode | 4 | **PASSED** |
| **`tests/unit/test_memory_lifecycle_and_bounds.py`** | 500-record ring buffer bounds, corrupt file baseline recovery, passive synaptic weight decay | 3 | **PASSED** |
| **`tests/unit/test_hasher.py`** | Fly-LSH $D=2048, k=102$ top-k sparsity, deterministic random projection, AST token extraction | 4 | **PASSED** |
| **`tests/unit/test_memory.py`** | Dopaminergic PAM reward / PPL1 punishment updates, synaptic weight bounds $[0.0, 5.0]$ | 2 | **PASSED** |
| **`tests/unit/test_reflex.py`** | MBON decision thresholds across `avoid`, `safe`, and `neutral` | 1 | **PASSED** |
| **`tests/e2e/test_mcp_api_hardening.py`** | Input validation, parameter clamping, aliases (`query`, `code`), compact mode, `-32601` method errors, resources read/list, ping | 7 | **PASSED** |
| **`tests/e2e/test_concurrency_stress.py`** | Async lock correctness and state integrity under 50 concurrent agent coroutines | 1 | **PASSED** |
| **`tests/e2e/test_outcome_validation.py`** | 15 parametrized valid and invalid input formats (rejects arbitrary strings, booleans, empty strings) | 15 | **PASSED** |
| **`tests/e2e/test_tool_annotations.py`** | MCP protocol annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) | 2 | **PASSED** |
| **`tests/e2e/test_mcp_stdio.py`** | End-to-end MCP JSON-RPC 2.0 stdio initialization, tool listing, and tool dispatch | 1 | **PASSED** |
| **`tests/integration/test_persistence.py`** | Atomic synaptic weight save/reload and persistent reflex evaluation across instances | 1 | **PASSED** |
| **`tests/e2e/test_release_followups.py`** | Hidden-failure recall across insertion orders, disk write error propagation, and stdio subprocess restart | 5 | **PASSED** |
| **`tests/benchmarks/test_token_economics.py`** | Schema token budget (<800 tokens), reflex response footprint (<80 tokens), and mathematical ROI modeling | 3 | **PASSED** |
| **`tests/unit/test_history_reuse_benchmark.py`** | Synthetic corpus integrity and repair validation, including hardcoded-value rejection | 4 | **PASSED** |
| **`tests/unit/test_history_usage.py`** | Negative savings, cache accounting, invalid telemetry and ineligible pairs | 3 | **PASSED** |
| **Total** | **59 passing test cases** | **59** | **100% PASS** |

> [!NOTE]
> **Persistence & Error Handling**: Synaptic weights and associative records persist locally in `~/.calyx/`. File writes use atomic replacements (`.tmp` to target). In the event of an I/O or filesystem error during disk persistence, an `OSError` is raised and propagated to the MCP caller with actionable diagnostics rather than falsely acknowledging successful recording.
>
> **Reflex Evaluation Invariant**: The reflex engine inspects qualifying failure records ($\ge 0.65$ similarity) before candidate truncation, ensuring previously identified bug patterns reliably trigger the `avoid` reflex even if multiple subsequent successes have been recorded for related code. Ordinary associative memory queries continue to return the nearest records across all outcomes.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
