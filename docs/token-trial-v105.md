# Actual agent-usage pilot on v1.0.5

Six fresh `gpt-5.6-luna` / medium sessions ran against runtime
`f7def05a9abad585d97f2d7e88844239f1757dab`. This pilot does **not demonstrate
token savings**. One pair met the protocol in both arms; it used 43,591 more
input-plus-output tokens with Calyx. The other two pairs are retained but
excluded because their Calyx calls failed or were never made.

## Frozen workload and control

The reused synthetic corpus has 100 lessons: three repair targets followed by
97 distinct authored distractors from `examples/history_lessons.json`. The
distractors are constructed examples, not observed or execution-verified project
incidents. The corpus and query-ranking logic were not tuned after the runs.

ON pre-seeds the corpus through the real Calyx memory API, then queries the
persisted history through a fresh stdio server. OFF exposes the same corpus
through a small lexical-search MCP helper. Both receive the same prompt asking
for exactly one query using the buggy function and `top_k=5`, then a repaired
function. OFF never receives the whole history in its prompt. This compares
Calyx to searchable saved notes, not to an agent deprived of past lessons.

The lexical helper counts identifier/operator matches in code and lesson text.
It is a simple reproducible baseline, not a claim to benchmark every search
system. Returned payload shapes differ between implementations.

The order was fixed before running: exact cache key OFF/ON, renamed integer-fee
ON/OFF, renamed inclusive pagination OFF/ON. Each task had one pair, with no
retries. All six saved patches passed restricted-AST validation and deterministic
checks covering different keys, units and slice bounds. A correct patch alone
does not prove that a stored lesson was retrieved or used.

## Results, including failed attempts

| Task | OFF input + output | ON input + output | OFF cached input | ON cached input | Pair eligible? |
| --- | ---: | ---: | ---: | ---: | --- |
| Exact cache key | 52,055 | 72,955 | 32,256 | 32,256 | No: Calyx call failed |
| Renamed fee | 52,337 | 55,137 | 32,256 | 32,256 | No: Calyx call missing |
| Renamed pagination | 52,783 | 96,374 | 32,256 | 71,680 | Yes |

For the cache task, the agent sent `query` instead of Calyx's required
`query_code`; the server rejected it. For the fee task, the agent returned a
correct patch without an actual MCP call. Those are observed client/protocol
failures, not evidence of a new memory-engine regression. They were not replaced
with successful reruns. All three OFF queries completed, but the pagination
query did not return its target lesson. The one successful ON query did return
that lesson. Retrieval and patch correctness are reported separately.

The sole eligible pair has savings of **-43,591 tokens (-82.59%)**. Its uncached
input plus output is 20,527 OFF and 24,694 ON; these are still not dollar costs.
Cached input is already included in input, and reasoning output is already
included in output. Neither subset is added again. No model-price assumptions
are used. One valid pair cannot establish a stable workload effect.

## Limits and reproducibility

This measures fresh single-turn agent usage with warm, locally seeded memory.
It does not measure the agent cost of discovering or recording lessons, nor an
amortized break-even point. Total usage includes the client's ordinary context
and tool loop. The experiment does not isolate context overhead from the
retrieval payload, and it does not measure a local dispatcher bypassing an LLM.
Earlier Astra and Luna trials on different revisions are not pooled here.

Run outputs must use fresh directories outside the checkout. These invocations
use a logged-in Codex CLI and consume model usage; no global MCP configuration
is changed. The host's unrelated `node_repl` MCP server is disabled for both arms.

```sh
python examples/benchmark_history_reuse.py --arm off --task cache-key \
  --output /path/to/new-results --model YOUR_MODEL --effort medium --order off
python examples/benchmark_history_reuse.py --arm on --task cache-key \
  --output /path/to/new-results --model YOUR_MODEL --effort medium --order off
# ceil-fee: ON then OFF, --order on. inclusive-page: OFF then ON, --order off.
```

The runner stops its invocation on an incomplete or noncompliant attempt while
retaining its events and metrics. Continue other predetermined tasks without
replacing the failed attempt. Only pair runs with equal model, effort, runtime,
corpus and acceptance checks. `runtime_revision` records the Git base; inspect
local runtime diffs as well when conducting a new experiment.

[`benchmarks/2026-09-14-v105`](../benchmarks/2026-09-14-v105) contains the six
sanitized event streams, prompts and result rows. Only the synthetic tool calls,
answers and usage are included, not full client context or private data. Recompute:

```sh
python examples/summarize_history_usage.py benchmarks/2026-09-14-v105/results.jsonl
```

The comparator preserves negative savings, rejects malformed usage, repeated
session IDs and mismatched models, and leaves savings null for ineligible pairs.
These are fresh sessions; do not feed it cumulative resume counters.
