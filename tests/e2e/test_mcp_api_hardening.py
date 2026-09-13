"""
End-to-End API Hardening & Error Contract Tests for Calyx MCP.
"""
import pytest


@pytest.mark.asyncio
async def test_empty_code_in_check_code_reflex_rejected(server):
    res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "check_code_reflex",
            "arguments": {"code": "   "}
        }
    })
    assert "error" in res
    assert res["error"]["code"] == -32000
    assert "non-empty" in res["error"]["message"]


@pytest.mark.asyncio
async def test_empty_code_in_remember_rejected(server):
    res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "remember_code_outcome",
            "arguments": {"code": "", "outcome": "success"}
        }
    })
    assert "error" in res
    assert res["error"]["code"] == -32000
    assert "non-empty" in res["error"]["message"]


@pytest.mark.asyncio
async def test_empty_query_in_query_associative_memory_rejected(server):
    res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "query_associative_memory",
            "arguments": {"query_code": ""}
        }
    })
    assert "error" in res
    assert res["error"]["code"] == -32000
    assert "non-empty" in res["error"]["message"]


@pytest.mark.asyncio
async def test_top_k_clamping_and_types(server):
    # Store one memory first
    await server.handle_request({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "remember_code_outcome",
            "arguments": {"code": "def valid(): pass", "outcome": "success"}
        }
    })

    # Test top_k as extreme number (should clamp to 50 without error)
    res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "query_associative_memory",
            "arguments": {"query_code": "def valid(): pass", "top_k": 99999}
        }
    })
    assert "result" in res

    # Test top_k as invalid string
    res_err = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "query_associative_memory",
            "arguments": {"query_code": "def valid(): pass", "top_k": "not_a_number"}
        }
    })
    assert "error" in res_err
    assert "integer" in res_err["error"]["message"]


@pytest.mark.asyncio
async def test_unknown_method_returns_standard_error(server):
    res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 7,
        "method": "non_existent_method",
        "params": {}
    })
    assert "error" in res
    assert res["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_resources_and_ping(server):
    # Ping
    ping_res = await server.handle_request({"jsonrpc": "2.0", "id": 8, "method": "ping", "params": {}})
    assert "result" in ping_res

    # Resources List
    res_list = await server.handle_request({"jsonrpc": "2.0", "id": 9, "method": "resources/list", "params": {}})
    assert len(res_list["result"]["resources"]) >= 1

    # Resources Read
    res_read = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 10,
        "method": "resources/read",
        "params": {"uri": "calyx://memory/metrics"}
    })
    assert "contents" in res_read["result"]
