"""Compare actual Codex exec --json usage; never infer tokens from tool latency.

Run with --off off.jsonl --on on.jsonl --expected-calls N.
Pass --off-passed and --on-passed only after independent acceptance checks.
Reads local files; emits aggregate JSON without prompts, code or machine paths.
"""
import argparse
import json
from pathlib import Path


def summarize(events, cumulative=False):
    usages = [e["usage"] for e in events if e.get("type") == "turn.completed" and "usage" in e]
    completed_turns = len(usages)
    items = [e.get("item", {}) for e in events if e.get("type") == "item.completed"]
    calls = [i for i in items if i.get("type") == "mcp_tool_call"]
    calyx_calls = [i for i in calls if i.get("tool") == "check_code_reflex"]
    complete_usage = bool(usages) and all(
        isinstance(u.get(key), int) and not isinstance(u.get(key), bool) and u[key] >= 0
        for u in usages for key in ("input_tokens", "output_tokens")
    )
    failed = any(e.get("type") in ("error", "turn.failed") for e in events)
    started_turns = sum(e.get("type") == "turn.started" for e in events)
    unfinished = started_turns > completed_turns
    failed_calls = sum(i.get("status") != "completed" or bool(i.get("error")) for i in calls)
    if cumulative:
        # Resumed Codex exec sessions repeat the lifetime counters. Do not sum them.
        for previous, current in zip(usages, usages[1:]):
            for key in ("input_tokens", "output_tokens", "cached_input_tokens"):
                if isinstance(previous.get(key), int) and isinstance(current.get(key), int) and current[key] < previous[key]:
                    raise ValueError("Cumulative usage decreased; do not combine different sessions")
        usages = usages[-1:]
    def total(key):
        values = [u.get(key) for u in usages]
        return sum(values) if values and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in values) else None
    return {
        "input_tokens": total("input_tokens"),
        "output_tokens": total("output_tokens"),
        "cached_input_tokens": total("cached_input_tokens"),
        "reasoning_output_tokens": total("reasoning_output_tokens"),
        "completed_turns": completed_turns,
        "mcp_calls": len(calls),
        "reflex_calls": len(calyx_calls),
        "failed_mcp_calls": failed_calls,
        "valid_usage": complete_usage and not failed and not unfinished and failed_calls == 0,
    }


def compare(off, on, off_passed=False, on_passed=False, expected_calls=1):
    if expected_calls < 1:
        raise ValueError("expected_calls must be positive")
    eligible = (off["valid_usage"] and on["valid_usage"] and off_passed and on_passed
                and off["reflex_calls"] == 0 and on["reflex_calls"] == expected_calls)
    baseline = off["input_tokens"] + off["output_tokens"] if off["valid_usage"] else None
    assisted = on["input_tokens"] + on["output_tokens"] if on["valid_usage"] else None
    saved = baseline - assisted if eligible else None
    return {
        "off": off, "on": on, "quality_matched": bool(off_passed and on_passed),
        "eligible": bool(eligible), "saved_tokens": saved,
        "saved_percent": 100 * saved / baseline if eligible and baseline else None,
        "accounting": "input + output; cached input and reasoning output are reported separately, not added again",
        "scope": "Only these sessions; include training sessions separately when computing cold-start or amortized savings.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--off", type=Path, required=True)
    parser.add_argument("--on", type=Path, required=True)
    parser.add_argument("--off-passed", action="store_true")
    parser.add_argument("--on-passed", action="store_true")
    parser.add_argument("--expected-calls", type=int, default=1)
    parser.add_argument("--cumulative", action="store_true", help="Each file contains cumulative snapshots from ONE resumed session")
    args = parser.parse_args()
    def read(path):
        return summarize([json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()], cumulative=args.cumulative)
    print(json.dumps(compare(read(args.off), read(args.on), args.off_passed, args.on_passed, args.expected_calls), indent=2))


if __name__ == "__main__":
    main()
