# Learning from wrong outcomes: validation stress test

The public tool schema allows only `success` and `failure`. At runtime revision
`18e505b`, the server did not enforce that enum: an arbitrary string was accepted
and treated as punishment. Omitting the outcome silently defaulted to failure.
This is distinct from the caller lying with a schema-valid `success` label.

The local benchmark uses actual stdio subprocesses and fresh temporary memory
for each scenario. It then restarts each server against its persisted memory.
No LLM is called. The fixed `print(hello)` fixture was separately executed under
Python `-I` and confirmed to raise `NameError`; the Calyx server never executes
submitted snippets.

| Input sequence | Observed behavior |
| --- | --- |
| `print('hello')`, outcome `I'm a banana` | Before fix: recorded as punishment, valence 0.775, then `avoid`, including after restart. |
| `print('hello')`, missing outcome | Before fix: recorded as failure and returned `avoid`. |
| Broken `print(hello)`, three `success` labels | Accepted; valence 1.45 and `safe`, including after restart. |
| Same broken code, failure then three successes | `avoid`, valence 1.225; the earlier failure remains among the three nearest records. |
| Same broken code, three successes then failure | **`safe`**, valence 1.225; the later failure is absent from the three returned nearest records. |

The final two rows expose an order-dependent limitation. Similarity ties retain
insertion order, and the reflex inspects only the top three records. Older
successes can hide a newer contradictory failure. This issue remains open;
the validation fix does not alter ranking, weights or existing stored records.

## Narrow fix in this PR

The MCP `remember_code_outcome` handler now requires an explicit string exactly
equal to `success` or `failure`, as advertised. Invalid strings, missing values
and wrong types return an error before any memory or disk changes. This is
boundary validation, not a full JSON-schema validator. The lower-level Python
memory API's historical aliases remain unchanged.

The actual stdio retest rejected the banana and missing labels, leaving fresh
memory neutral at valence 1.0 across restart. Parameterized tests also check
that invalid requests preserve existing weights, records and persisted bytes.
Four rejection cases failed against the old handler before this fix.

The tool description now states that outcomes are caller-reported and that
Calyx does not independently verify them. A `safe` reflex means rewarded
association, not tested correctness. Preventing false-success learning would
need trusted test evidence/provenance and a conflict policy; executing arbitrary
submitted code inside the MCP process is not the fix.

## Reproduce

```sh
python examples/benchmark_learning_validation.py --output /path/to/results.json
```

The checked-in evidence is in
[`benchmarks/2026-09-13-validation`](../benchmarks/2026-09-13-validation).
`before.json` contains the first four scenarios against `18e505b`; `after.json`
adds the reversed-order case and shows all five after enum validation. The
runner and evidence use only synthetic fixtures.
