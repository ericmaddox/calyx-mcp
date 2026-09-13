"""Local stdio stress test of outcome validation and falsely labelled learning.

No LLM or private code is used. Only the fixed print(hello) fixture is executed,
in a separate Python process; the MCP server must never execute submitted code.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def exchange(storage, calls):
    requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}]
    requests.extend({"jsonrpc": "2.0", "id": index, "method": "tools/call",
                     "params": {"name": name, "arguments": arguments}}
                    for index, (name, arguments) in enumerate(calls, 2))
    env = dict(os.environ, CALYX_STORAGE_DIR=str(storage))
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run([sys.executable, "-m", "calyx_mcp.server"],
                            input="".join(json.dumps(r) + "\n" for r in requests),
                            capture_output=True, text=True, env=env, check=True, timeout=20)
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert [r["id"] for r in responses] == list(range(1, len(requests) + 1))
    return [{"request": request, "response": response}
            for request, response in zip(requests[1:], responses[1:])]


def run():
    failure = subprocess.run([sys.executable, "-I", "-c", "print(hello)"],
                             capture_output=True, text=True, timeout=10)
    assert failure.returncode != 0 and "NameError" in failure.stderr
    scenarios = [
        ("invalid-outcome", "print('hello')", [{"outcome": "I'm a banana"}]),
        ("missing-outcome", "print('hello')", [{}]),
        ("false-success", "print(hello)", [{"outcome": "success"}] * 3),
        ("conflicting-outcomes", "print(hello)",
         [{"outcome": "failure", "error_message": "Verified NameError: hello is undefined"}]
         + [{"outcome": "success"}] * 3),
        ("late-failure", "print(hello)", [{"outcome": "success"}] * 3
         + [{"outcome": "failure", "error_message": "Verified NameError: hello is undefined"}]),
    ]
    rows = []
    with tempfile.TemporaryDirectory(prefix="calyx-validation-") as folder:
        for name, code, labels in scenarios:
            storage = Path(folder) / name
            calls = [("check_code_reflex", {"code": code})]
            calls += [("remember_code_outcome", {"code": code, **label}) for label in labels]
            calls += [("check_code_reflex", {"code": code}),
                      ("query_associative_memory", {"query_code": code, "top_k": 5})]
            transcript = exchange(storage, calls)
            restarted = exchange(storage, [("check_code_reflex", {"code": code})])
            rows.append({"scenario": name, "code": code, "exchanges": transcript,
                         "after_restart": restarted})
    return {"fixture_failure": {"code": "print(hello)", "exit_code": failure.returncode,
                                "exception": "NameError"}, "scenarios": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for row in result["scenarios"]:
        response = row["after_restart"][0]["response"]
        print(row["scenario"], response.get("result", response))
