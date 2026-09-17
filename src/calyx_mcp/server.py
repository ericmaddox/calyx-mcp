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
            raw_code = args.get("code") or args.get("code_snippet") or args.get("query_code") or args.get("query")
            if not raw_code or not isinstance(raw_code, str) or not raw_code.strip():
                raise ValueError("Must provide non-empty 'code' string to evaluate reflex.")
            context = args.get("context") or args.get("language")
            outcome = await self.reflex_engine.evaluate_reflex(raw_code, context)
            return outcome.__dict__

        elif name == "remember_code_outcome":
            raw_code = args.get("code") or args.get("code_snippet") or args.get("query_code")
            if not raw_code or not isinstance(raw_code, str) or not raw_code.strip():
                raise ValueError("Must provide non-empty 'code' string.")
            outcome_val = args.get("outcome")
            if not isinstance(outcome_val, str) or outcome_val not in ("success", "failure"):
                raise ValueError("outcome must be 'success' or 'failure'; it is required")
            error_msg = args.get("error_message") or args.get("lesson")
            tags = args.get("tags")
            return await self.memory.remember(raw_code, outcome_val, error_msg, tags)

        elif name == "query_associative_memory":
            query_code = args.get("query_code") or args.get("query") or args.get("code") or args.get("code_snippet")
            if not query_code or not isinstance(query_code, str) or not query_code.strip():
                raise ValueError("Must provide non-empty 'query_code' string.")
            try:
                top_k = int(args.get("top_k", 5))
            except (ValueError, TypeError):
                raise ValueError("top_k must be a valid integer.")
            top_k = max(1, min(top_k, 50))
            compact = bool(args.get("compact", False))
            matches = await self.memory.query_similarity(query_code, top_k=top_k)
            if compact:
                matches = [
                    {
                        "id": m["id"],
                        "similarity": m["similarity"],
                        "outcome": m["outcome"],
                        "error_message": m.get("error_message", "")
                    }
                    for m in matches
                ]
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
    """CLI entrypoint for calyx-mcp / calyx-server"""
    import argparse
    from pathlib import Path
    from .installer import inspect_targets, install_to_target, install_all_detected, init_agents_md

    # Check for subcommands or default server mode
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        parser = argparse.ArgumentParser(prog="calyx-mcp install", description="Install Calyx MCP into IDE configuration files")
        parser.add_argument("--all", action="store_true", help="Install into all detected IDEs")
        parser.add_argument("--target", type=str, help="Specific IDE target (claude, cursor, antigravity, windsurf, roo, cline, zed)")
        parser.add_argument("--mode", type=str, default="python", choices=["python", "uvx"], help="Invocation command mode (python or uvx)")
        parser.add_argument("--status", action="store_true", help="Show detected IDEs and configuration status")
        args = parser.parse_args(sys.argv[2:])

        if args.status or (not args.all and not args.target):
            targets = inspect_targets()
            print("\n=== Calyx MCP Target Discovery ===")
            for t in targets:
                det_str = "[Detected]" if t.detected else "[Not Found]"
                cfg_str = "[Configured]" if t.configured else "[Not Configured]"
                print(f"  * {t.name:<22} {det_str:<12} {cfg_str:<16} ({t.config_path})")
            print("\nRun 'calyx-mcp install --all' or 'calyx-mcp install --target <name>' to configure.")
            return

        if args.all:
            results = install_all_detected(mode=args.mode)
            print("\n=== Calyx MCP Installation Results ===")
            for name, success, msg in results:
                icon = "[OK]" if success else "[ERROR]"
                print(f"  {icon} {name}: {msg}")
            return

        if args.target:
            success, msg = install_to_target(args.target.lower(), mode=args.mode)
            icon = "[OK]" if success else "[ERROR]"
            print(f"{icon} {msg}")
            return

    elif len(sys.argv) > 1 and sys.argv[1] == "init":
        parser = argparse.ArgumentParser(prog="calyx-mcp init", description="Initialize AGENTS.md in current or target workspace")
        parser.add_argument("--path", type=str, default=".", help="Target workspace directory")
        parser.add_argument("--force", action="store_true", help="Overwrite existing AGENTS.md")
        args = parser.parse_args(sys.argv[2:])

        created, dest = init_agents_md(target_dir=Path(args.path), overwrite=args.force)
        if created:
            print(f"[OK] Created Calyx agent directives in {dest}")
        else:
            print(f"[NOTE] AGENTS.md already exists at {dest}. Use --force to overwrite.")
        return

    # Default server invocation
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
