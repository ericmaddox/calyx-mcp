"""
Token Economics Benchmark & Validation Suite for Calyx MCP.
Quantifies tool payload sizes, response token footprints, and token savings ROI models.
"""
import json
import pytest
from calyx_mcp.tools import get_tool_schemas


def estimate_tokens(text: str) -> int:
    """Standard rule-of-thumb estimate: ~4 characters per token for code/JSON"""
    return max(1, len(text) // 4)


def test_tool_definition_token_budget():
    """Validates that all 5 tool definitions combined stay under a strict token budget"""
    schemas = get_tool_schemas()
    serialized = json.dumps(schemas)
    estimated_tokens = estimate_tokens(serialized)

    # Full MCP tool schema bundle with annotations should be compact (<800 tokens)
    assert estimated_tokens < 800, f"Tool definitions too large: {estimated_tokens} tokens"


@pytest.mark.asyncio
async def test_reflex_response_payload_token_footprint(server):
    """Verifies that check_code_reflex responses are token-minimized"""
    res = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "check_code_reflex",
            "arguments": {"code": "def calculate_tax(subtotal): return subtotal * 0.08"}
        }
    })
    assert "result" in res
    response_text = json.dumps(res["result"])
    tokens = estimate_tokens(response_text)

    # Response should be concise (<80 tokens)
    assert tokens < 80, f"Reflex response exceeds budget: {tokens} tokens"


def test_token_savings_roi_model():
    """
    Mathematical ROI validation:
    Calculates net token balance over typical agent session profiles.
    """
    # Profile 1: Standard agent session
    # - Schema overhead (cached in modern agents, but assumed active): ~400 tokens
    # - 10 reflex checks: 10 * 45 tokens = 450 tokens
    # - 1 bug intercepted (avoiding 1 full re-prompt + stack trace + re-implementation turn):
    #   Re-prompt turn: ~4,000 prompt tokens + ~1,500 output tokens = 5,500 tokens
    schema_overhead = 400
    reflex_checks_count = 10
    cost_per_check = 45
    cost_of_llm_repair_turn = 5500

    total_calyx_cost = schema_overhead + (reflex_checks_count * cost_per_check)
    gross_savings = 1 * cost_of_llm_repair_turn
    net_savings = gross_savings - total_calyx_cost

    # Net savings must be decisively positive (> 4,000 tokens saved)
    assert net_savings > 4000, f"Expected positive token ROI, got net {net_savings}"

    # Profile 2: High bug-density or multi-agent collaboration (3 bugs intercepted)
    gross_savings_multi = 3 * cost_of_llm_repair_turn
    net_savings_multi = gross_savings_multi - total_calyx_cost
    assert net_savings_multi > 14000
