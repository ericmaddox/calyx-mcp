"""
End-to-End validation for MCP Tool Annotations.
"""
import pytest


@pytest.mark.asyncio
async def test_tool_annotations_present_in_tools_list(server):
    res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    })
    assert "result" in res
    tools_map = {t["name"]: t for t in res["result"]["tools"]}

    # Verify all 5 tools exist
    assert len(tools_map) == 5

    # Check read-only tools
    read_only_tools = ["check_code_reflex", "query_associative_memory", "inspect_memory_state"]
    for tool_name in read_only_tools:
        tool = tools_map[tool_name]
        assert "annotations" in tool, f"Tool {tool_name} missing annotations"
        assert tool["annotations"]["readOnlyHint"] is True
        assert tool["annotations"]["openWorldHint"] is False

    # Check mutating tools
    mutating_tools = ["remember_code_outcome", "reset_memory"]
    for tool_name in mutating_tools:
        tool = tools_map[tool_name]
        assert "annotations" in tool, f"Tool {tool_name} missing annotations"
        assert tool["annotations"]["readOnlyHint"] is False
        assert tool["annotations"]["destructiveHint"] is True
        assert tool["annotations"]["idempotentHint"] is False
        assert tool["annotations"]["openWorldHint"] is False


@pytest.mark.asyncio
async def test_readonly_tools_do_not_mutate_state(server):
    # 1. Inspect initial state
    init_state = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "inspect_memory_state",
            "arguments": {}
        }
    })
    assert "result" in init_state

    # 2. Call check_code_reflex (read-only)
    await server.handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "check_code_reflex",
            "arguments": {"code": "def hello(): print('world')"}
        }
    })

    # 3. Call query_associative_memory (read-only)
    await server.handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "query_associative_memory",
            "arguments": {"query_code": "def hello(): print('world')"}
        }
    })

    # 4. Inspect state again - verify zero memories added
    post_state = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "inspect_memory_state",
            "arguments": {}
        }
    })
    assert init_state["result"]["content"] == post_state["result"]["content"]
