# Measuring Calyx in an agent workflow

Calyx does not call an LLM. Its local CPU time and the tokens used by an agent
calling its tools are different measurements. Count tool schemas, arguments,
results, context replay, retries and reasoning in the agent run. A similarity
warning does not replace acceptance tests.

## Reproduce the local experiment

```sh
python -m pip install -e '.[dev]'
python -m pytest
python examples/benchmark_reflex.py --samples 100 > reflex-results.json
```

This benchmark runs three synthetic families with fresh memory, one recorded
failure per family, exact/renamed/fixed/unrelated checks, then ten warmups and 100
timed exact recalls per family. It reports in-process median and p95 latency;
startup, persistence and MCP transport are excluded. It returns
`agent_tokens_saved: null`, because no agent baseline was measured by this script.
Results include each snippet and its input contract. Safe controls matter as
much as recalling a known bug. Increasing repeats improves timing measurement,
not the number of independent code examples.

## Collect actual agent usage

For Codex, capture `codex exec --json` stdout for each independent run. Its
`turn.completed.usage` reports input, output and cached-input tokens. Other
clients need their own telemetry adapters; do not substitute model estimates.
[Codex non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode).

```sh
python examples/compare_agent_usage.py --off off.jsonl --on on.jsonl \
  --expected-calls 4 --off-passed --on-passed
```

Only pass the acceptance flags after independently checking equivalent outcomes.
The comparator rejects missing usage, failed runs, failed MCP calls, missing
expected reflex calls, and missing acceptance. It preserves negative savings.
It prints aggregate metrics only, without copying prompts or code. Keep raw
logs local until reviewed for private data. With one fresh session per file,
the original command applies directly. **Resumed Codex runs report cumulative
session counters:** use `--cumulative` when each input file combines snapshots
from one resumed session. Summing those snapshots double-counts earlier turns.
For incremental continuation costs, subtract the previous snapshot; see the
[learned-reuse follow-up](reuse-results.md), which cross-checks those deltas
against the session rollout counters.

Use the same model, effort, starting task and acceptance criteria. Run OFF/ON
and ON/OFF in separate fresh sessions and repeat on multiple tasks. Freeze each
warm-memory snapshot before the pair; never train on held-out answers. Report
cold-start training separately and amortize it explicitly for warm workloads.
Record elapsed time, source revision, cache counts, retry counts and completion
rates alongside usage. Include failed runs in the outcome report even when they
cannot enter a quality-matched savings comparison.

For matched runs, saved tokens = OFF(input + output) - ON(input + output).
Cached input is a subset of input. For this Codex event schema, reasoning output
is reported separately but is already included in output; neither is added again.
Cost is a separate calculation requiring the actual model's cached/uncached
prices. Do not compare just uncached tokens while claiming total-token savings.

## Initial warm-memory pilot (2026-09-13)

Source: `61480b12f3531e931f5beb93422243be158ebfc6`, package 1.0.2, Windows 11,
Python 3.12.14, NumPy 2.3.5, Codex CLI 0.154.0-alpha.6.2, gpt-6-astra with medium
reasoning. This is a small, deliberately bounded code-review pilot, **not** a
representative coding benchmark or evidence about all Calyx workloads.

The same four snippets were supplied to each fresh agent:

```python
# A: buggy for x in [-1000, 1000]
def scale(x): return x / 0
# B: correct for x in [-1000, 1000]
def scale(x): return x / 1
# C: buggy for a nonempty list
def last(xs): return xs[len(xs)]
# D: correct for a nonempty list
def last(xs): return xs[len(xs)-1]
```

Both arms received the lessons "division by literal zero raises" and "index
len(xs) is out of bounds." ON memory was locally pre-seeded with A and C as
failures. Agents classified each snippet and gave a short reason; the evaluator
required A/C buggy and B/D correct. ON was instructed to make four reflex calls;
OFF reviewed directly. Therefore this measures the incremental cost of mandatory
recall on an easy review with equally available history. It does not measure
retrieval replacing a large historical context. No LLM training cost was incurred
by pre-seeding; production learning overhead is not represented.

| Pair / order | OFF input | OFF output | ON input | ON output | ON cached input | Saved total tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 3 / ON then OFF | 17,189 | 109 | 53,718 | 339 | 34,944 | -36,759 (-212.50%) |
| 4 / OFF then ON | 17,332 | 117 | 53,674 | 321 | 47,488 | -36,546 (-209.44%) |

Both arms passed all four classifications in both pairs. Each ON run completed
four MCP checks. Elapsed OFF/ON seconds were 8.313/22.922 and 8.781/21.984.
OFF cached-input tokens were zero. The broad default agent context is included;
tool turns replay that context. Cache variability and shared client settings
limit causal interpretation. These are two repetitions of **one task**, not two
independent tasks. Total tokens increased in this pilot; pricing was not measured.

Aggregate evidence and stripped usage/tool-status events are in
[`benchmarks/2026-09-13`](../benchmarks/2026-09-13). Recompute, for example:

```sh
python examples/compare_agent_usage.py \
  --off benchmarks/2026-09-13/pair-3-off.jsonl \
  --on benchmarks/2026-09-13/pair-3-on.jsonl \
  --expected-calls 4 --off-passed --on-passed
```

Calibration runs are retained with exclusions: pair 1 allowed arbitrary finite
integers, and the agent correctly identified float-conversion overflow in B,
invalidating the evaluator's label. Pair 2's ON calls were blocked by client
approval policy. Neither pair contributes to savings. Valid upstream ON runs
used an invocation-only approval for the inspected read-only reflex tool.

## Recall limitations and client hints

The original five-family local trial recalled 5/5 exact bugs, 0/5 renamed
variants, and warned on 4/5 corrected versions; the smaller checked-in benchmark
lets contributors reproduce three of those families with explicit contracts.
No identifier-normalization fix or new semantic classifier is claimed here.
In particular, A and B above have identical fingerprints at the tested revision:
numeric literal values are not included in the current features. D also remains
similar to C despite the repaired index. Treat these as advisory matches; review
the actual code. Changing the feature representation needs a separate design for
existing persisted weights and records.

The three read tools now expose `readOnlyHint: true` and `openWorldHint: false`.
Learning and reset explicitly remain writes, destructive and non-idempotent:
learning alters existing weights, and resets can create backups. A real stdio
test checks the catalog, and a behavioral test verifies that reading preserves
both in-memory state and persisted bytes. Annotations are optional advisory
metadata, not authorization or a protocol-version upgrade. Client policy can
still require approval.
The modified catalog was also exercised in Codex CLI 0.154.0-alpha.6.2 with a
read-only sandbox: one reflex call completed without a per-tool approval
override. This integration smoke test is separate from the upstream token pairs.
[MCP ToolAnnotations](https://modelcontextprotocol.io/specification/2025-06-18/schema#toolannotations).
