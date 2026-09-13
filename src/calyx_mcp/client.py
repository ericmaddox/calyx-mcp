"""
CLI Test & Diagnostic Tool for Calyx MCP (`calyx-client`)
"""

import sys
import json
import asyncio
from typing import Dict, Any, Optional
from .server import create_mcp_server


class CalyxClient:
    """Terminal client for interacting with Calyx MCP"""

    def __init__(self, config_path: Optional[str] = None):
        self.server = create_mcp_server(config_path)

    async def initialize(self) -> Dict[str, Any]:
        return await self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        })

    async def list_tools(self) -> Dict[str, Any]:
        return await self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments}
        })


def main() -> None:
    """CLI entrypoint for calyx-client"""
    client = CalyxClient()

    async def run_demo():
        print("=== Calyx MCP Server Diagnostic ===")
        init_res = await client.initialize()
        print(f"Connected: {init_res['result']['serverInfo']['name']} v{init_res['result']['serverInfo']['version']}")

        print("\n=== Checking Memory State ===")
        metrics_res = await client.call_tool("inspect_memory_state", {})
        print(json.dumps(metrics_res, indent=2))

        print("\n=== Testing Code Reflex Check ===")
        sample_code = "def divide(a, b): return a / b"
        reflex_res = await client.call_tool("check_code_reflex", {"code": sample_code})
        print(json.dumps(reflex_res, indent=2))

    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
