"""Real, billable Codex same-session pilot; run explicitly with a configured login.

Python 3.9+, installed numpy/Calyx and Codex CLI required. No global settings change.
Each invocation creates ONE session and resumes it three times; it does not fork.
Outputs are local. Inspect them before sharing. Acceptance is independent of Calyx.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


INITIAL = [
    {"id": "A", "code": "def scale(x): return x / 0"},
    {"id": "B", "code": "def scale(x): return x / 1"},
    {"id": "C", "code": "def last(xs): return xs[len(xs)]"},
    {"id": "D", "code": "def last(xs): return xs[len(xs)-1]"},
]
CHANGED = [
    {"id": "A", "code": "def normalize(value): return value / 1"},
    {"id": "B", "code": "def normalize(value): return value / 0"},
    {"id": "C", "code": "def tail(values): return values[len(values)-1]"},
    {"id": "D", "code": "def tail(values): return values[len(values)]"},
]
SCHEMA = {"type": "object", "properties": {"results": {"type": "array", "items": {
    "type": "object", "properties": {"id": {"type": "string"}, "bug": {"type": "boolean"},
    "reason": {"type": "string"}}, "required": ["id", "bug", "reason"], "additionalProperties": False,
}}}, "required": ["results"], "additionalProperties": False}


def expected_results(cases):
    """Execute only the fixed, author-owned pure fixtures over boundary examples."""
    assert cases in (INITIAL, CHANGED)
    expected = {}
    for case in cases:
        namespace = {}
        exec(case["code"], namespace)
        fn = next(v for k, v in namespace.items() if k != "__builtins__")
        values = (-1000, 0, 1000) if case["id"] in ("A", "B") else ([1], [1, 2], [1, 2, 3])
        raised = []
        for value in values:
            try:
                fn(value)
                raised.append(False)
            except (ZeroDivisionError, IndexError):
                raised.append(True)
        assert len(set(raised)) == 1
        expected[case["id"]] = raised[0]
    return expected


def accepted(answer, expected):
    rows = answer.get("results", [])
    return (len(rows) == len(expected) and all(type(r.get("bug")) is bool for r in rows)
            and {r.get("id"): r.get("bug") for r in rows} == expected)


def cumulative_delta(current, previous):
    keys = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens")
    if any(type(current.get(k)) is not int or current[k] < previous.get(k, 0) for k in keys):
        raise ValueError("Missing or decreasing cumulative usage")
    return {key: current[key] - previous.get(key, 0) for key in keys}


def usage_snapshot(thread_id):
    """Read only usage and turn-context fields from THIS newly created pilot session."""
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    matches = list((home / "sessions").rglob("*" + thread_id + "*.jsonl"))
    if len(matches) != 1:
        return None
    latest = None
    model = None
    for line in matches[0].read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        payload = event.get("payload", {})
        if event.get("type") == "turn_context":
            model = payload.get("model", model)
        if event.get("type") == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info")
            if info and info.get("total_token_usage"):
                latest = info["total_token_usage"]
    return {"total": latest, "model": model} if latest else None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", choices=["off", "on"], required=True)
    ap.add_argument("--replicate", type=int, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--effort", required=True)
    ap.add_argument("--disable-mcp", action="append", default=[])
    args = ap.parse_args()
    repo = Path(__file__).resolve().parents[1]
    out = args.output.resolve() / ("rep-%s-%s" % (args.replicate, args.arm))
    out.mkdir(parents=True, exist_ok=False)
    workspace = out / "workspace"
    workspace.mkdir()
    revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    schema_path = out / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    overrides = {"model": args.model, "model_reasoning_effort": args.effort}
    for server in args.disable_mcp:
        overrides["mcp_servers." + server + ".enabled"] = False
    if args.arm == "on":
        sys.path.insert(0, str(repo / "src"))
        from calyx_mcp.config import CalyxConfig
        from calyx_mcp.server import CalyxMCPServer
        cfg = CalyxConfig()
        cfg.storage.storage_dir = str(out / "memory")
        server = CalyxMCPServer(cfg)
        async def seed():
            for i, lesson in [(0, "Division by zero raises."), (2, "Index len(xs) is out of bounds.")]:
                await server.memory.remember(INITIAL[i]["code"], "failure", lesson)
        asyncio.run(seed())
        overrides.update({
            "mcp_servers.calyx_continuation.command": sys.executable,
            "mcp_servers.calyx_continuation.args": ["-m", "calyx_mcp.server"],
            "mcp_servers.calyx_continuation.env.PYTHONPATH": str(repo / "src"),
            "mcp_servers.calyx_continuation.env.CALYX_STORAGE_DIR": str(out / "memory"),
            "mcp_servers.calyx_continuation.required": True,
            "mcp_servers.calyx_continuation.enabled_tools": ["check_code_reflex"],
        })
    base = [shutil.which("codex"), "exec", "--skip-git-repo-check", "--json", "--sandbox", "read-only"]
    for key, value in overrides.items():
        base += ["-c", key + "=" + json.dumps(value)]
    first = ("Review the four synthetic Python snippets below. Classify whether each raises for valid inputs. "
             "x/value is an integer in [-1000,1000]; xs/values is a nonempty ordinary list. "
             "Return one result per ID with a short reason. Historical lessons: division by zero raises; "
             "index equal to list length is out of bounds. Do not inspect files, execute commands, browse, "
             "delegate or modify anything. Memory warnings are fallible; check actual code. "
             + ("For THIS INITIAL TURN ONLY, call check_code_reflex once per snippet. In subsequent turns "
                "use it only if useful; no mandatory recheck. " if args.arm == "on" else "Review without tools. ")
             + json.dumps(INITIAL))
    prompts = [first, "LGTM. Run the same review again.", "LGTM. Run it again.",
               "Now review these changed snippets under the same input assumptions. Do not reuse the old "
               "classifications blindly. Use available tools only if useful. Return one result per ID. " + json.dumps(CHANGED)]
    thread_id = None
    records = []
    previous_total = {"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0, "reasoning_output_tokens": 0}
    previous_exec = dict(previous_total)
    for turn, prompt in enumerate(prompts):
        prefix = out / ("turn-%s" % turn)
        prefix.with_suffix(".prompt.txt").write_text(prompt, encoding="utf-8")
        command = list(base)
        if thread_id:
            command += ["resume", "--output-schema", str(schema_path), "-o", str(prefix.with_suffix(".answer.json")), thread_id, "-"]
        else:
            command += ["--output-schema", str(schema_path), "-o", str(prefix.with_suffix(".answer.json")), "-"]
        start = time.monotonic()
        with prefix.with_suffix(".events.jsonl").open("w", encoding="utf-8") as stdout, prefix.with_suffix(".stderr.log").open("w", encoding="utf-8") as stderr:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, cwd=workspace, text=True)
            process.communicate(prompt)
        elapsed = time.monotonic() - start
        events = [json.loads(line) for line in prefix.with_suffix(".events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        started = [e["thread_id"] for e in events if e.get("type") == "thread.started"]
        if started:
            if thread_id:
                assert started[-1] == thread_id, "Resume changed session ID"
            thread_id = started[-1]
        usages = [e["usage"] for e in events if e.get("type") == "turn.completed" and "usage" in e]
        calls = [e["item"] for e in events if e.get("type") == "item.completed" and e.get("item", {}).get("type") == "mcp_tool_call"]
        answer_file = prefix.with_suffix(".answer.json")
        answer = json.loads(answer_file.read_text()) if answer_file.exists() else {}
        snapshot = usage_snapshot(thread_id) if thread_id else None
        delta = None
        if snapshot:
            delta = {key: snapshot["total"].get(key, 0) - previous_total.get(key, 0) for key in previous_total}
            previous_total = {key: snapshot["total"].get(key, 0) for key in previous_total}
        raw = usages[-1] if len(usages) == 1 else None
        incremental = cumulative_delta(raw, previous_exec) if raw else None
        if raw:
            previous_exec = raw
        record = {"arm": args.arm, "replicate": args.replicate, "turn": turn,
                  "stage": ["initial", "repeat_1", "repeat_2", "changed"][turn], "source_revision": revision,
                  "model": args.model, "effort": args.effort, "elapsed_seconds": round(elapsed, 3),
                  "acceptance_passed": accepted(answer, expected_results(CHANGED if turn == 3 else INITIAL)),
                  "exit_code": process.returncode, "mcp_calls": len(calls),
                  "failed_mcp_calls": sum(c.get("status") != "completed" or bool(c.get("error")) for c in calls),
                  "raw_exec_usage": raw, "rollout_usage_delta": delta,
                  "incremental_usage": incremental, "usage_crosscheck_passed": incremental is not None and incremental == delta,
                  "snapshot_model": snapshot["model"] if snapshot else None}
        records.append(record)
        (out / "metrics.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
        print(json.dumps(record), flush=True)
        if process.returncode or not raw or not record["acceptance_passed"] or record["failed_mcp_calls"]:
            raise RuntimeError("Invalid turn retained; stopping this session")
        if not record["usage_crosscheck_passed"]:
            raise RuntimeError("Usage could not be corroborated against this session's cumulative counters")
        if turn == 0 and len(calls) != (4 if args.arm == "on" else 0):
            raise RuntimeError("Initial tool-use protocol not met")


if __name__ == "__main__":
    main()
