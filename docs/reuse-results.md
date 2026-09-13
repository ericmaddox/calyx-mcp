# Follow-up: learn once and reuse (2026-09-13)

The first pilot forced tool calls in fresh sessions. This follow-up tests the
intended reuse scenarios directly, using the same gpt-6-astra/medium configuration
and Calyx runtime at `19725b50d817e8c9ab2b2ea7fdbf5daa4fbae96c`. No hashing or
learning algorithm was changed. Python 3.12.14, NumPy 2.3.5, Windows 11 and Codex
CLI 0.154.0-alpha.6.2 were used. The two experiment runners are checked in with
their synthetic prompts and sanitized results.

## Same-session "LGTM, run it again"

Four sessions: replicate 1 OFF then ON; replicate 2 ON then OFF. Each initial
review was followed, by explicit session ID, by:

1. "LGTM. Run the same review again."
2. "LGTM. Run it again."
3. Changed snippets: rename the variables/functions and reverse all four expected
   bug classifications, preventing blind repetition from passing.

The initial ON turn queried four pre-trained patterns. **Later ON turns were
free to skip tools.** OFF had the same prior lessons and same conversation
history. Each ON session kept its own memory across server restarts. This
experiment isolates conversation reuse; initial memory was locally pre-seeded,
so it does not measure the cost of agent-driven learning.

All 16 turns passed, including the changed-code controls. Neither ON agent used
Calyx on any continuation. Both OFF and ON reused their conversation; this
cannot be credited uniquely to Calyx.

Numbers below are **incremental input + output**, including cached input:

| Replicate | Continuation | OFF total | ON total | OFF cached input | ON cached input |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Repeat 1 | 18,096 | 21,041 | 17,664 | 18,560 |
| 1 | Repeat 2 | 18,212 | 21,155 | 17,792 | 20,736 |
| 1 | Changed code | 18,432 | 21,377 | 17,920 | 20,864 |
| 2 | Repeat 1 | 18,096 | 19,030 | 17,664 | 18,560 |
| 2 | Repeat 2 | 18,212 | 19,144 | 17,792 | 18,688 |
| 2 | Changed code | 18,432 | 21,393 | 17,920 | 18,816 |

Repeating the review used far fewer tokens than the initial mandatory ON review
(55,141 / 55,164), but it did not reach zero and did not beat the OFF control in
total tokens. Cached input is not newly generated text and may be priced
differently. For example, OFF Repeat 1 had 323 uncached input + 109 output tokens,
in addition to 17,664 cached input tokens. This report makes no cost claim.
Host-provided context and caching varied despite fixed model/effort settings;
do not interpret small differences as stable model effects.

### Accounting correction verified against actual sessions

For OFF replicate 1, `codex exec --json` emitted input counters 17,869, 35,856,
53,959 and 72,286. Those are cumulative across resumes, not individual turn
costs. Output likewise accumulated 109, 218, 327, 432. The runner subtracts
successive counters and corroborates **all 16 turn deltas** against the same
session's persisted `total_token_usage` snapshots. Only numeric usage/model
fields were read; full rollouts are not published. The original fresh-session
pair measurements are unaffected because each had only one top-level turn.

## Verified learning, then reuse in fresh sessions

Eight fresh agent sessions: OFF learn + three repairs, then ON learn + three
repairs. Each call restarted the MCP process while retaining ON's memory folder.
This directly tests persistent Calyx learning, independently of conversation
history. There was no hidden pre-seeding in this experiment.

The harness reproduced a cache-key failure: `cache_key('ABC', 'X')` returned
`'ABC'`, but the verified project convention required `('X', 'ABC')` (venue,
symbol). The ON agent called `remember_code_outcome` once with that failure.
After restart, three fresh agents called `query_associative_memory` and repaired
the exact implementation, a parameter-renamed variant and a function/parameter-
renamed variant. Each generated patch had to pass three deterministic checks,
preserve the function signature and remain a restricted pure return expression.

OFF agents received their previously written concise lesson as a note, including
the expected output type and ordering. This is a strong baseline for this small
one-lesson task. It compares two ways of reusing a known lesson, not Calyx memory
against an agent deliberately deprived of the required project convention.

**Calyx recorded and retrieved the lesson successfully. All six repairs passed.**
Training cost is included below:

| Stage | OFF total tokens | ON total tokens | OFF cached input | ON cached input |
| --- | ---: | ---: | ---: | ---: |
| Learn verified outcome | 17,244 | 52,606 | 0 | 34,304 |
| Reuse exact pattern | 17,244 | 52,820 | 0 | 34,560 |
| Reuse renamed parameters | 17,249 | 52,828 | 14,720 | 34,560 |
| Reuse renamed function/parameters | 17,247 | 52,451 | 0 | 34,304 |
| **Total, including learning** | **68,984** | **210,705** | **14,720** | **137,728** |

Total-token savings were -141,721. Excluding cached input from both totals gives
54,264 versus 72,977 uncached input + output tokens; these are still not prices.
The one-tool-call agent loop replayed substantial default client context.
This demonstrates functioning learned reuse but no token advantage over compact
notes **on this one family**. It does not estimate benefit on large histories,
many distractors, harder repairs or a client that dispatches local reflexes
without invoking an LLM. The OFF/ON order for this learning family was not
counterbalanced; repeat it before generalizing timing or cache effects.

## Reproduce and inspect

These commands use a logged-in Codex CLI and consume account usage. Run them
explicitly; outputs must point outside this repository and use fresh directories.
Keep the same model and effort for every arm. On this host, the unrelated
`node_repl` server was disabled in both arms using `--disable-mcp node_repl`.
There were no global MCP/config changes or worktrees.

```sh
python examples/benchmark_continuations.py --arm off --replicate 1 \
  --output /path/to/results/continuations --model YOUR_MODEL --effort medium
python examples/benchmark_continuations.py --arm on --replicate 1 \
  --output /path/to/results/continuations --model YOUR_MODEL --effort medium
# Replicate 2: run ON first, then OFF, with --replicate 2.

python examples/benchmark_learned_reuse.py --arm off \
  --output /path/to/results/learning --model YOUR_MODEL --effort medium
python examples/benchmark_learned_reuse.py --arm on \
  --output /path/to/results/learning --model YOUR_MODEL --effort medium
```

Both runners record actual usage, prompts, answers and tool results locally.
The continuation runner verifies session IDs remain identical; the learning
runner verifies they differ. Learning writes are approved only for this trial's
fresh synthetic memory; reuse exposes read-only query tools. Neither runner
sends messages, modifies global configuration, or reads a personal corpus.

[`benchmarks/2026-09-13-reuse`](../benchmarks/2026-09-13-reuse) contains sanitized
events, prompts and result ledgers. Recompute the whole-session continuation
pair (including the initial turn) from cumulative counters:

```sh
python examples/compare_agent_usage.py \
  --off benchmarks/2026-09-13-reuse/rep-1-off.jsonl \
  --on benchmarks/2026-09-13-reuse/rep-1-on.jsonl \
  --cumulative --expected-calls 4 --off-passed --on-passed
```

Per-continuation deltas and cross-check results are in
`continuation-results.jsonl`. Fresh-session learning and repair costs are in
`learned-reuse-results.jsonl`; each row is one fresh run, so sum those rows once.
