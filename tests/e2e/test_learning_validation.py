"""Invalid outcome labels must not alter learned memory."""
import json
import pytest


@pytest.mark.parametrize("label", ["I'm a banana", "", "passed", None, 1, [], {}])
@pytest.mark.asyncio
async def test_rejects_invalid_outcomes_without_mutation(server, label):
    await server.execute_tool("remember_code_outcome", {"code": "x = 1", "outcome": "success"})
    weights = server.memory.weights.copy()
    records = json.dumps(server.memory.records)
    files = {p.name: p.read_bytes() for p in server.memory.storage_dir.iterdir()}
    response = await server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "remember_code_outcome", "arguments": {"code": "print('hello')", "outcome": label}}})
    assert "error" in response
    assert (server.memory.weights == weights).all()
    assert json.dumps(server.memory.records) == records
    assert {p.name: p.read_bytes() for p in server.memory.storage_dir.iterdir()} == files


@pytest.mark.asyncio
async def test_missing_outcome_does_not_default_to_failure(server):
    response = await server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "remember_code_outcome", "arguments": {"code": "print('hello')"}}})
    assert "error" in response
    assert server.memory.records == []


@pytest.mark.asyncio
async def test_success_is_a_claim_not_code_verification(server):
    # Deliberately broken code: accepting a valid label does not prove execution.
    code = "print(hello)"
    for _ in range(3):
        await server.execute_tool("remember_code_outcome", {"code": code, "outcome": "success"})
    assert (await server.execute_tool("check_code_reflex", {"code": code}))["status"] == "safe"
