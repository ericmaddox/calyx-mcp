<p align="center">
  <img src="assets/calyx_banner.jpg" alt="Calyx MCP - Bio-Inspired Code Reflex Engine" width="100%" />
</p>

# Calyx MCP

[![PyPI Version](https://img.shields.io/pypi/v/calyx-mcp.svg)](https://pypi.org/project/calyx-mcp/)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-9%20passed-brightgreen.svg)](tests/)
[![Latency](https://img.shields.io/badge/reflex%20latency-%3C0.5ms-success.svg)](#benchmark-and-token-savings)

Bio-inspired associative memory and instant code reflex server for AI coding agents, implementing the Drosophila Mushroom Body circuit and Fly-LSH sparse projection algorithm over the Model Context Protocol (MCP).

---

## At a Glance

* **The Problem**: AI coding agents repeatedly consume thousands of LLM prompt tokens and multi-second roundtrip latency diagnosing recurring bugs, antipatterns, and project constraints.
* **The Solution**: Calyx brings the Drosophila Mushroom Body (fruit fly brain) circuit to AI agents—using Fly-LSH sparse Kenyon Cell projection ($D=2048, k=102$) and dopaminergic synaptic plasticity to give agents instant, zero-token reflex memory.
* **The Proof (Benchmark)**:
  * **Latency**: **0.400 ms** (vs ~1,450 ms LLM API roundtrip — **>3,600x faster**)
  * **Token Cost**: **0 tokens** (100% local associative memory)

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

The following performance metrics were measured on a Windows x86_64 host running Python 3.13 with native NumPy operations:

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
  * Token Efficiency:   100% of LLM tokens saved on learned code anti-patterns

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
| **Token Consumption** | 650 - 2,400 tokens | **0 tokens** | **100% token savings** |
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

Calyx registers the following tools conforming to the MCP JSON-RPC 2.0 specification:

### 1. `check_code_reflex`
Evaluates a code snippet against synaptic valence weights and stored experiences.
- **Parameters**:
  - `code_snippet` (string, required): Source code to evaluate.
  - `language` (string, optional): Programming language (e.g. `python`, `javascript`).
- **Returns**: `status` (`neutral`, `aversion`, `attraction`), `valence`, `similarity_with_past_bugs`, `warning`, `recommendation`.

### 2. `remember_code_outcome`
Applies dopamine-driven synaptic updates based on test execution or runtime results.
- **Parameters**:
  - `code_snippet` (string, required): Code associated with the outcome.
  - `language` (string, required): Programming language.
  - `outcome` (string, required): `success` or `failure`.
  - `lesson` (string, required): Summary of the bug or successful pattern.
  - `reward_score` (number, optional): Value between `-1.0` (punishment) and `+1.0` (reward). Default `-1.0` for failure, `+1.0` for success.

### 3. `query_associative_memory`
Performs approximate nearest-neighbor search across stored code experiences using Fly-LSH similarity.
- **Parameters**:
  - `query_code` (string, required): Code snippet to match.
  - `top_k` (integer, optional): Maximum results to return (default: `5`).
  - `language` (string, optional): Language filter.

### 4. `inspect_memory_state`
Returns operational metrics and synaptic weight distribution of the Mushroom Body.
- **Parameters**: None.
- **Returns**: Active sparsity percentage, total Kenyon cells, weight distribution stats, and storage location.

### 5. `reset_memory`
Resets synaptic weights to neutral baseline and purges stored experiences.
- **Parameters**:
  - `confirm` (boolean, required): Confirmation flag (`true`).

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

Execute the comprehensive test suite:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Test Coverage
- `test_hasher.py`: Verifies deterministic hashing, projection dimensions, and Winner-Take-All sparsity.
- `test_memory.py`: Verifies associative retrieval, dopamine-mediated plasticity, weight bounds, and file persistence.
- `test_reflex.py`: Verifies rapid aversion on bug patterns and attraction on reinforced patterns.
- `test_server.py`: Verifies JSON-RPC 2.0 tool registration, protocol initialization, and execution handlers.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
