# Retrieval from a larger synthetic history (2026-09-13)

This follow-up compares Calyx associative recall with a read-only lexical search
over the same saved lessons. It uses gpt-5.6-luna at medium effort, fresh Codex
sessions, and the Calyx runtime at `18e505b703a98f4eb3dbf7abd1f031218d336d88`.
It is separate from the earlier Astra trials; their absolute token counts must
not be pooled as if they used the same model and task.

## Frozen protocol

The history contains three repair targets followed by 97 distinct authored
synthetic code/lesson pairs, in the checked-in order. The distractors cover
numeric operations, sequences, strings, mappings, predicates, dates and paths.
They are constructed examples, not observed incidents from a real project.
Only the three target repairs have executable acceptance checks in this trial.
The 97-record file is `examples/history_lessons.json`, with SHA-256
`710e9c2ce5b6f58c507742083c0e7ecd5493ea2be695bce1d22ec832450c9898`.

Each ON run preloads all 100 lessons as failures through Calyx's local memory
API and starts a separate MCP server against that persisted memory. Each OFF
run makes the same history available through a small lexical-search MCP server.
Both agents must issue one query with the supplied buggy function and request
five results. Neither receives the entire history in its prompt. This compares
two retrieval implementations; OFF is not a model deprived of saved lessons.

Three pairs run in a fixed, alternating order:

1. Namespaced cache-key repair, exact trained code: OFF then ON.
2. Integer ceiling fee repair, renamed function and parameters: ON then OFF.
3. Inclusive pagination repair, renamed function and parameters: OFF then ON.

The same restricted Python patch validator applies to each pair. It preserves
the original signature and permits only a pure return expression with a narrow
AST allowlist. Target retrieval and passing repair are separate measurements:
a model can infer a correct fix even when the relevant lesson is absent.
Missed retrievals and wrong repairs remain outcomes, rather than disappearing
from the sample. Infrastructure failures are reported separately.

This is a warm-history experiment. Local ingestion duration is reported, but
the corpus was authored and seeded without an LLM training session. It does not
measure or amortize agent-driven lesson discovery and recording. The earlier
[learn-then-reuse trial](reuse-results.md) includes that stage for one family.
The history stays below Calyx's persisted 500-record cap. All records are
failures; this trial exercises associative queries, not reflex calibration
under a representative success/failure mixture.

## Interpretation limits

There is one pair per task, with no repeated sampling within a pair. Alternating
order reduces a simple ordering confound but does not make three synthetic
tasks a representative or statistically stable workload benchmark. Returned
payloads and tool schemas differ as they would for these implementations.
The host's default client context and cache behavior also contribute to usage.

Total tokens mean actual CLI input plus output. Cached input is a subset of
input and is shown separately, never added twice. These are token measurements,
not dollar costs. Only fresh, single-turn sessions are used here, so resumed
cumulative-counter differencing is unnecessary.

## Observed results

All six final patches passed deterministic acceptance, including additional
key, divisor and slice cases added during harness review and applied to the
saved answers without rerunning the models. Five sessions made the required
real MCP call. The fee OFF agent instead emitted tool-call-like text in an
answer and then supplied a correct patch; that pair is excluded from the
matched retrieval-cost comparison. It was not silently retried.

| Task | OFF input + output | ON input + output | OFF cached input | ON cached input | Target returned OFF / ON |
| --- | ---: | ---: | ---: | ---: | --- |
| Exact cache key | 53,727 | 75,279 | 32,256 | 51,456 | yes / yes |
| Renamed fee | 33,466 | 99,628 | 14,080 | 68,608 | no call / no |
| Renamed pagination | 53,899 | 93,838 | 32,256 | 70,656 | no / yes |

Calyx retrieved the intended lesson in 2/3 queries; lexical search did so in
1/2 actual queries. Both implementations missed lessons, and successful patches
without a returned target show why repair success alone is not evidence of
learned reuse. Calyx found the renamed pagination lesson that lexical search
missed, but neither the three tasks nor this small search implementation support
a general retrieval-quality claim.

The two protocol-compliant, quality-matched pairs used **21,552 and 39,939 more
total tokens with Calyx**. This larger-history pilot still does not demonstrate
token savings. Local Calyx ingestion took 1.046, 1.219 and 0.812 seconds for the
three independently seeded histories; these are not agent learning costs.

Three earlier launch attempts failed before a session started because Codex
could not locate its home directory; usage was unavailable, not assumed zero.
A subsequent two-session cache calibration used the repository working
directory and a process-local home override. Both patches and queries passed,
with OFF 51,291 and ON 89,237 total tokens. Those runs are retained separately
because their launch context differs from the six fixed-protocol runs. The
fixed protocol uses isolated artifact working directories and inherited host
configuration without a home override. No global configuration was modified.

## Evidence and reproduction

[`benchmarks/2026-09-13-history`](../benchmarks/2026-09-13-history) contains all
six synthetic event streams, prompts, result rows and the five calibration
records. `protocol_compliant` distinguishes the missing real call; the original
runner's `infrastructure_valid` combined telemetry and protocol requirements.
No full client context or private corpus is published.

```sh
python examples/benchmark_history_reuse.py --arm off --task cache-key \
  --output /path/to/fresh-results --model YOUR_MODEL --effort medium --order off
python examples/benchmark_history_reuse.py --arm on --task cache-key \
  --output /path/to/fresh-results --model YOUR_MODEL --effort medium --order off
# ceil-fee: ON then OFF, --order on; inclusive-page: OFF then ON, --order off.
```

Each invocation consumes model usage and writes a fresh directory. Preserve
noncompliance and failures when aggregating; do not rerun until a passing sample
appears. The later [learning-validation fix](learning-validation.md) does not
change hashing or retrieval, but changes a tool description; reruns on the PR's
latest source need not reproduce historical token counts exactly.
