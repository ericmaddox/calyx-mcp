"""
End-to-End JSON-RPC 2.0 MCP Protocol validation
"""
import pytest
from calyx_mcp.server import CalyxMCPServer


@pytest.mark.asyncio
async def test_full_mcp_protocol_flow(server):
    # 1. Initialize
    init_res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    })
    assert init_res["result"]["protocolVersion"] == "2024-11-05"
    assert init_res["result"]["serverInfo"]["name"] == "calyx-mcp"

    # 2. Tools List
    tools_res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    })
    tools = [t["name"] for t in tools_res["result"]["tools"]]
    assert "check_code_reflex" in tools
    assert "remember_code_outcome" in tools
    assert "query_associative_memory" in tools
    assert "inspect_memory_state" in tools
    assert "reset_memory" in tools

    # 3. Tool Call: check_code_reflex
    call_res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "check_code_reflex",
            "arguments": {"code": "def divide(a, b): return a / b"}
        }
    })
    assert "content" in call_res["result"]
    assert call_res["result"]["content"][0]["type"] == "text"
