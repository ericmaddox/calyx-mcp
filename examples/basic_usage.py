"""
Standalone demonstration of Calyx MCP
"""

import asyncio
from calyx_mcp.server import create_mcp_server


async def main():
    print("=== 1. Starting Calyx MCP Server ===")
    server = create_mcp_server()
    await server.initialize()

    # Broken code patch with ZeroDivisionError
    buggy_code = """
def calculate_ratio(items, total):
    # Bug: total could be 0!
    return len(items) / total
"""

    print("\n=== 2. Pre-Check Code Reflex (Before learning) ===")
    reflex_1 = await server.execute_tool("check_code_reflex", {"code": buggy_code})
    print(f"Status: {reflex_1['status']} (Valence: {reflex_1['valence']}, Confidence: {reflex_1['confidence']})")

    print("\n=== 3. Unit Test Fails -> Dopamine Punishment (-1.0) ===")
    learn_res = await server.execute_tool("remember_code_outcome", {
        "code": buggy_code,
        "outcome": "failure",
        "error_message": "ZeroDivisionError: division by zero when total=0",
        "tags": ["math", "zero_division"]
    })
    print(f"Outcome Recorded: {learn_res['outcome']} (Pattern Valence dropped to: {learn_res['pattern_valence']})")

    print("\n=== 4. Re-Checking Code Reflex (After learning) ===")
    reflex_2 = await server.execute_tool("check_code_reflex", {"code": buggy_code})
    print(f"Status: {reflex_2['status'].upper()}! (Valence: {reflex_2['valence']})")
    print(f"Warning: {reflex_2['warning']}")
    print(f"Recommendation: {reflex_2['recommendation']}")

    # Working fix
    fixed_code = """
def calculate_ratio(items, total):
    if total <= 0:
        return 0.0
    return len(items) / total
"""
    print("\n=== 5. Working Fix Applied -> Dopamine Reward (+1.0) ===")
    await server.execute_tool("remember_code_outcome", {
        "code": fixed_code,
        "outcome": "success",
        "tags": ["math", "safe_division"]
    })

    print("\n=== 6. Checking Fixed Code Reflex ===")
    reflex_3 = await server.execute_tool("check_code_reflex", {"code": fixed_code})
    print(f"Status: {reflex_3['status'].upper()} (Valence: {reflex_3['valence']})")


if __name__ == "__main__":
    asyncio.run(main())
