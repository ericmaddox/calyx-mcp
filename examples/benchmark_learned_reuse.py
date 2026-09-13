"""Explicit billable learn-then-reuse trial in four independent Codex sessions.

The ON agent records a verified failure, then retrieves it after server restarts.
OFF receives its previously written lesson as a compact note: a strong memory baseline.
Only synthetic fixtures are used. Generated patches are restricted to pure return ASTs.
"""
import argparse
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

TRAINED = "def cache_key(symbol, venue): return symbol"
VARIANTS = [TRAINED, "def cache_key(ticker, market): return ticker", "def lookup_key(asset, exchange): return asset"]
CONTRACT = "The cache key must be the tuple (venue, symbol), with venue first."
LESSON = "Verified failure: cache_key('ABC', 'X') returned 'ABC'; expected ('X', 'ABC'). " + CONTRACT


def validate_patch(code, original=None):
    try:
        tree = ast.parse(code)
        allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Tuple, ast.Name, ast.Load, ast.Constant)
        if any(not isinstance(node, allowed) for node in ast.walk(tree)):
            return False
        if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
            return False
        function = tree.body[0]
        if original:
            previous = ast.parse(original).body[0]
            if function.name != previous.name or [a.arg for a in function.args.args] != [a.arg for a in previous.args.args]:
                return False
        if (function.decorator_list or function.returns or len(function.body) != 1
                or not isinstance(function.body[0], ast.Return) or len(function.args.args) != 2
                or function.args.defaults or function.args.vararg or function.args.kwarg
                or function.args.kwonlyargs or any(arg.annotation for arg in function.args.args)):
            return False
        namespace = {"__builtins__": {}}
        exec(compile(tree, "<synthetic-patch>", "exec"), namespace)
        fn = namespace[function.name]
        return all(fn(symbol, venue) == (venue, symbol) for symbol, venue in [("ABC", "X"), ("ABC", "Y"), ("DEF", "X")])
    except (SyntaxError, ValueError, TypeError, KeyError, NameError):
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", choices=["off", "on"], required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--effort", required=True)
    ap.add_argument("--disable-mcp", action="append", default=[])
    args = ap.parse_args()
    repo = Path(__file__).resolve().parents[1]
    out = args.output.resolve() / args.arm
    out.mkdir(parents=True, exist_ok=False)
    revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    assert not validate_patch(TRAINED), "Known failing fixture unexpectedly passed"
    assert validate_patch("def cache_key(symbol, venue): return (venue, symbol)")
    records = []
    thread_ids = []
    note = None
    for stage in range(4):
        run = out / str(stage)
        run.mkdir()
        overrides = {"model": args.model, "model_reasoning_effort": args.effort}
        for server in args.disable_mcp:
            overrides["mcp_servers." + server + ".enabled"] = False
        if args.arm == "on":
            overrides.update({
                "mcp_servers.calyx_learned.command": sys.executable,
                "mcp_servers.calyx_learned.args": ["-m", "calyx_mcp.server"],
                "mcp_servers.calyx_learned.env.PYTHONPATH": str(repo / "src"),
                "mcp_servers.calyx_learned.env.CALYX_STORAGE_DIR": str(out / "memory"),
                "mcp_servers.calyx_learned.required": True,
                "mcp_servers.calyx_learned.enabled_tools": ["remember_code_outcome"] if stage == 0 else ["query_associative_memory"],
            })
            if stage == 0:
                # Explicitly authorized write, restricted to this trial's fresh synthetic memory.
                overrides["mcp_servers.calyx_learned.tools.remember_code_outcome.approval_mode"] = "approve"
        field = "lesson" if stage == 0 else "code"
        schema = {"type": "object", "properties": {field: {"type": "string"}}, "required": [field], "additionalProperties": False}
        schema_path = run / "schema.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        prompt = "This is a bounded synthetic trial. Do not inspect files, run shell commands, browse, delegate, or modify files. "
        if stage == 0:
            prompt += "A deterministic test has already verified this failure: " + LESSON + " Code: " + TRAINED + ". "
            if args.arm == "on":
                prompt += "Record this exact code once with remember_code_outcome, outcome failure, and an error_message capturing the verified expected tuple and ordering. "
            prompt += "Return a concise lesson preserving the required output type and ordering. Do not repair code yet."
        else:
            prompt += "Repair this function to conform to the project's previously verified cache-key convention. "
            prompt += ("Retrieve the previous lesson with query_associative_memory using this code before repairing it. " if args.arm == "on"
                       else "Previously recorded project lesson: " + note + " ")
            prompt += "Code: " + VARIANTS[stage - 1] + ". Return only the corrected function as the code field. "
            prompt += "Keep its name and two parameters, use one pure return expression, and no imports, calls, decorators, or annotations."
        (run / "prompt.txt").write_text(prompt, encoding="utf-8")
        command = [shutil.which("codex"), "exec", "--ephemeral", "--skip-git-repo-check", "--json", "--sandbox", "read-only"]
        for key, value in overrides.items():
            command += ["-c", key + "=" + json.dumps(value)]
        command += ["--output-schema", str(schema_path), "-o", str(run / "answer.json"), "-"]
        start = time.monotonic()
        with (run / "events.jsonl").open("w", encoding="utf-8") as stdout, (run / "stderr.log").open("w", encoding="utf-8") as stderr:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, cwd=run, text=True)
            process.communicate(prompt)
        events = [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        ids = [e["thread_id"] for e in events if e.get("type") == "thread.started"]
        assert len(ids) == 1 and ids[0] not in thread_ids, "Each reuse must start a fresh agent session"
        thread_ids.extend(ids)
        usage = [e["usage"] for e in events if e.get("type") == "turn.completed" and "usage" in e]
        calls = [e["item"] for e in events if e.get("type") == "item.completed" and e.get("item", {}).get("type") == "mcp_tool_call"]
        answer = json.loads((run / "answer.json").read_text()) if (run / "answer.json").exists() else {}
        if stage == 0:
            note = answer.get("lesson", "")
            passed = all(word in note.lower() for word in ("tuple", "venue", "symbol"))
            if args.arm == "on":
                memory = json.loads((out / "memory" / "memory_registry.json").read_text())
                passed = passed and len(memory) == 1 and memory[0]["code_snippet"] == TRAINED and memory[0]["outcome"] == "failure"
        else:
            passed = validate_patch(answer.get("code", ""), VARIANTS[stage - 1])
        record = {"arm": args.arm, "stage": stage, "kind": "learn" if stage == 0 else "reuse_" + str(stage),
                  "source_revision": revision, "model": args.model, "effort": args.effort,
                  "elapsed_seconds": round(time.monotonic() - start, 3), "acceptance_passed": passed,
                  "exit_code": process.returncode, "usage": usage[-1] if len(usage) == 1 else None,
                  "mcp_calls": len(calls), "failed_mcp_calls": sum(c.get("status") != "completed" or bool(c.get("error")) for c in calls)}
        records.append(record)
        (out / "metrics.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
        print(json.dumps(record), flush=True)
        if process.returncode or not record["usage"] or not passed or record["failed_mcp_calls"]:
            raise RuntimeError("Invalid run retained; stop before dependent reuse")
        if len(calls) != (1 if args.arm == "on" else 0):
            raise RuntimeError("Learn/retrieve protocol not met")


if __name__ == "__main__":
    main()
