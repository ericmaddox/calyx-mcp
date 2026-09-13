"""
Calyx MCP Server: Model Context Protocol standard implementation (2024-11-05)
"""

import sys
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .config import CalyxConfig, get_default_config
from .memory import MushroomBodyMemory
from .reflex import ReflexDecisionEngine
from .tools import calyx_tools_registry, get_tool_schemas


class CalyxMCPServer:
    """Calyx MCP Server Instance"""

    def __init__(self, config: Optional[CalyxConfig] = None):
        self.config = config or get_default_config()
        self.logger = self._setup_logging()
        self.server_info = {
            "name": self.config.server.server_name,
            "version": self.config.server.version,
            "description": "Neuro-Symbolic Associative Code Memory MCP Server powered by the Fruit Fly Mushroom Body"
        }
        
        # Initialize Memory and Reflex Engine
        self.memory = MushroomBodyMemory(
            plasticity_cfg=self.config.plasticity,
            storage_cfg=self.config.storage
        )
        self.reflex_engine = ReflexDecisionEngine(self.memory)

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("calyx_mcp")
        logger.setLevel(getattr(logging, self.config.server.log_level.upper(), logging.INFO))
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not logger.handlers:
            logger.addHandler(handler)
        return logger

    async def initialize(self) -> Dict[str, Any]:
        """Handle MCP initialize handshake"""
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": self.server_info,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False}
            }
        }

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Dispatch incoming MCP JSON-RPC 2.0 requests"""
        req_id = request.get("id")
        method = request.get("method") or request.get("type", "unknown")
        params = request.get("params", {})

        # Ignore JSON-RPC notifications (no id)
        if req_id is None and (method.startswith("notifications/") or method == "initialized"):
            self.logger.debug(f"Received notification: {method}")
            return None

        try:
            if method in ["initialize", "init"]:
                res = await self.initialize()
                return self._jsonrpc_success(req_id, res)
                
            elif method in ["notifications/initialized", "initialized"]:
                return None

            elif method == "tools/list":
                tools = calyx_tools_registry.get_all_tools()
                return self._jsonrpc_success(req_id, {"tools": tools})
                
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result_data = await self.execute_tool(tool_name, tool_args)
                return self._jsonrpc_success(req_id, {
                    "content": [{"type": "text", "text": json.dumps(result_data, indent=2)}]
                })
                
            elif method == "resources/list":
                resources = [
                    {
                        "uri": "calyx://memory/metrics",
                        "name": "Calyx Synaptic Health",
                        "mimeType": "application/json",
                        "description": "Live Mushroom Body synaptic weight statistics"
                    }
                ]
                return self._jsonrpc_success(req_id, {"resources": resources})
                
            elif method == "resources/read":
                uri = params.get("uri")
                metrics = await self.memory.get_state_metrics()
                return self._jsonrpc_success(req_id, {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(metrics, indent=2)
                    }]
                })

            elif method == "prompts/list":
                return self._jsonrpc_success(req_id, {"prompts": []})
                
            elif method == "ping":
                return self._jsonrpc_success(req_id, {})
                
            else:
                if req_id is None:
                    return None
                return self._jsonrpc_error(req_id, -32601, f"Method not found: {method}")

        except Exception as e:
            self.logger.error(f"Error processing {method}: {e}")
            if req_id is None:
                return None
            return self._jsonrpc_error(req_id, -32000, str(e))

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific Calyx tool"""
        if name == "check_code_reflex":
            code = args.get("code") or args.get("code_snippet", "")
            context = args.get("context") or args.get("language")
            outcome = await self.reflex_engine.evaluate_reflex(code, context)
            return outcome.__dict__

        elif name == "remember_code_outcome":
            code = args.get("code") or args.get("code_snippet", "")
            outcome_val = args.get("outcome")
            if not isinstance(outcome_val, str) or outcome_val not in ("success", "failure"):
                raise ValueError("outcome must be 'success' or 'failure'; it is required")
            error_msg = args.get("error_message") or args.get("lesson")
            tags = args.get("tags")
            return await self.memory.remember(code, outcome_val, error_msg, tags)

        elif name == "query_associative_memory":
            query_code = args.get("query_code") or args.get("code", "")
            top_k = int(args.get("top_k", 5))
            matches = await self.memory.query_similarity(query_code, top_k=top_k)
            return {"query": query_code[:100], "matches_count": len(matches), "matches": matches}

        elif name == "inspect_memory_state":
            return await self.memory.get_state_metrics()

        elif name == "reset_memory":
            if not args.get("confirm", False):
                raise ValueError("Must provide 'confirm: true' to reset memory.")
            backup = args.get("backup", True)
            return await self.memory.reset(backup=backup)

        else:
            raise ValueError(f"Unknown tool: {name}")

    def _jsonrpc_success(self, req_id: Any, result: Any) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _jsonrpc_error(self, req_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    async def run_stdio(self) -> None:
        """Run standard I/O JSON-RPC loop for Claude Desktop / Cursor / Antigravity"""
        self.logger.info("Calyx MCP Server running on stdio transport...")
        loop = asyncio.get_running_loop()
        
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            line_str = line.strip()
            if not line_str:
                continue
            try:
                req = json.loads(line_str)
                response = await self.handle_request(req)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                self.logger.error(f"Error in stdio stream: {e}")
                err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


def create_mcp_server(config_path: Optional[str] = None) -> CalyxMCPServer:
    cfg = CalyxConfig.from_file(config_path) if config_path else get_default_config()
    return CalyxMCPServer(cfg)


def main() -> None:
    """CLI entrypoint for calyx-server"""
    import argparse
    parser = argparse.ArgumentParser(description="Calyx MCP Server")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--transport", type=str, default="stdio", choices=["stdio", "sse"], help="Transport mode")
    parser.add_argument("--log-level", type=str, default="INFO", help="Log level")
    args = parser.parse_args()

    server = create_mcp_server(args.config)
    try:
        asyncio.run(server.run_stdio())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
