"""
End-to-End validation for 'outcome' parameter in remember_code_outcome tool.
"""
import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_outcome", [
    "invalid",
    "I'm a banana",
    "SUCCESS",
    "Failure",
    "pass",
    "fail",
    "",
    123,
    True,
    False,
    [],
    {},
])
async def test_invalid_outcome_rejected(server, invalid_outcome):
    res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "remember_code_outcome",
            "arguments": {
                "code": "def foo(): pass",
                "outcome": invalid_outcome
            }
        }
    })
    assert "error" in res
    assert res["error"]["code"] == -32000
    assert "outcome must be 'success' or 'failure'" in res["error"]["message"]


@pytest.mark.asyncio
async def test_missing_outcome_rejected(server):
    res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "remember_code_outcome",
            "arguments": {
                "code": "def foo(): pass"
            }
        }
    })
    assert "error" in res
    assert res["error"]["code"] == -32000
    assert "outcome must be 'success' or 'failure'" in res["error"]["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize("valid_outcome", ["success", "failure"])
async def test_valid_outcome_accepted(server, valid_outcome):
    res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "remember_code_outcome",
            "arguments": {
                "code": "def test_ok(): assert True",
                "outcome": valid_outcome
            }
        }
    })
    assert "result" in res
    assert "error" not in res
    assert "content" in res["result"]
    assert res["result"]["content"][0]["type"] == "text"
