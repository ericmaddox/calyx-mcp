"""Tool hints match both the public catalog and actual memory effects."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_annotations_are_exposed_over_stdio(tmp_path):
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    env = dict(os.environ, CALYX_STORAGE_DIR=str(tmp_path))
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    result = subprocess.run(
        [sys.executable, "-m", "calyx_mcp.server"],
        input="".join(json.dumps(request) + "\n" for request in requests),
        capture_output=True, text=True, env=env, timeout=15, check=True,
    )
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert [response["id"] for response in responses] == [1, 2]
    tools = {tool["name"]: tool for tool in responses[1]["result"]["tools"]}
    for name in ("check_code_reflex", "query_associative_memory", "inspect_memory_state"):
        assert tools[name]["annotations"]["readOnlyHint"] is True
        assert tools[name]["annotations"]["openWorldHint"] is False
    for name in ("remember_code_outcome", "reset_memory"):
        assert tools[name]["annotations"]["readOnlyHint"] is False
    assert tools["reset_memory"]["annotations"]["destructiveHint"] is True
    assert tools["remember_code_outcome"]["annotations"]["idempotentHint"] is False


@pytest.mark.asyncio
async def test_read_tools_preserve_persisted_and_in_memory_state(server):
    code = "def ratio(x): return x / 0"
    await server.execute_tool("remember_code_outcome", {"code": code, "outcome": "failure"})
    weights = server.memory.weights.copy()
    records = json.dumps(server.memory.records, sort_keys=True)
    before = {p.name: p.read_bytes() for p in server.memory.storage_dir.iterdir()}
    for name, arguments in (
        ("check_code_reflex", {"code": code}),
        ("query_associative_memory", {"query_code": code}),
        ("inspect_memory_state", {}),
    ):
        await server.execute_tool(name, arguments)
    assert (weights == server.memory.weights).all()
    assert records == json.dumps(server.memory.records, sort_keys=True)
    assert before == {p.name: p.read_bytes() for p in server.memory.storage_dir.iterdir()}
