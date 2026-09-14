"""Regression coverage for the v1.0.4 release review."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("recent", [True, False])
async def test_failure_is_not_hidden_by_five_successes(server, recent):
    code = "print(hello)"
    failure = {"code": code + " # failure", "outcome": "failure"}
    if not recent:
        await server.execute_tool("remember_code_outcome", failure)
    for _ in range(5):
        await server.execute_tool("remember_code_outcome", {"code": code, "outcome": "success"})
    if recent:
        await server.execute_tool("remember_code_outcome", failure)
    # Public retrieval still ranks exact successes first; the reflex must look
    # for failures before truncating its own candidates.
    matches = await server.memory.query_similarity(code, top_k=5)
    assert all(m["outcome"] == "success" for m in matches)
    result = await server.execute_tool("check_code_reflex", {"code": code})
    assert result["status"] == "avoid"
    assert result["similarity_with_past_bugs"] >= 0.65


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["weights", "metadata"])
async def test_failed_save_returns_error_to_mcp_caller(server, monkeypatch, stage):
    if stage == "weights":
        def deny(*args, **kwargs):
            raise PermissionError("synthetic write denial")
        monkeypatch.setattr("calyx_mcp.memory.np.savez_compressed", deny)
    else:
        original = Path.replace
        def deny_metadata(path, target):
            if Path(target) == server.memory.metadata_path:
                raise PermissionError("synthetic metadata replacement denial")
            return original(path, target)
        monkeypatch.setattr(Path, "replace", deny_metadata)
    response = await server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "remember_code_outcome",
                   "arguments": {"code": "x = 1", "outcome": "failure"}},
    })
    assert "error" in response
    assert "persist" in response["error"]["message"].lower()
    assert "result" not in response


def test_stdio_learning_survives_process_restart(tmp_path):
    env = dict(os.environ, CALYX_STORAGE_DIR=str(tmp_path))
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")

    def run(calls):
        requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"}]
        requests += [{"jsonrpc": "2.0", "id": i, "method": "tools/call",
                      "params": {"name": name, "arguments": args}}
                     for i, (name, args) in enumerate(calls, 2)]
        process = subprocess.run([sys.executable, "-m", "calyx_mcp.server"],
            input="".join(json.dumps(r) + "\n" for r in requests),
            text=True, capture_output=True, timeout=20, check=True, env=env)
        responses = [json.loads(line) for line in process.stdout.splitlines()]
        assert [r["id"] for r in responses] == list(range(1, len(calls) + 2))
        return [json.loads(r["result"]["content"][0]["text"]) for r in responses[1:]]

    code = "print(hello)"
    learned = run([("remember_code_outcome", {"code": code, "outcome": "success"})] * 5
                  + [("remember_code_outcome", {"code": code + " # failure", "outcome": "failure"})])
    assert all(result["status"] == "recorded" for result in learned)
    reloaded = run([("check_code_reflex", {"code": code})])
    assert reloaded[0]["status"] == "avoid"
