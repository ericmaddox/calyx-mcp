"""
MCP Tool definitions and JSON schemas for Calyx MCP
Strict conformance to Model Context Protocol specification 2024-11-05.
"""

from typing import Dict, Any, List, Optional


class CalyxToolRegistry:
    """Registry of Calyx MCP Tools"""

    def __init__(self):
        self._tools = {
            "check_code_reflex": {
                "name": "check_code_reflex",
                "description": "Instant (<1ms) associative memory check of proposed code against past rewarded or punished bug patterns. Returns 'avoid', 'safe', or 'neutral'.",
                "annotations": {
                    "readOnlyHint": True,
                    "openWorldHint": False
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The proposed code snippet, function, or diff to evaluate."
                        },
                        "context": {
                            "type": "string",
                            "description": "Optional context or filename describing the task."
                        }
                    },
                    "required": ["code"]
                }
            },
            "remember_code_outcome": {
                "name": "remember_code_outcome",
                "description": "Applies one-shot dopamine reward (test passed) or punishment (test failed/bug) to Mushroom Body synaptic weights.",
                "annotations": {
                    "readOnlyHint": False,
                    "destructiveHint": True,
                    "idempotentHint": False,
                    "openWorldHint": False
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The code snippet that was executed or tested."
                        },
                        "outcome": {
                            "type": "string",
                            "enum": ["success", "failure"],
                            "description": "The outcome of testing the code: 'success' (rewards synapses) or 'failure' (punishes synapses)."
                        },
                        "error_message": {
                            "type": "string",
                            "description": "Optional error trace or description if the outcome was 'failure'."
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags (e.g. ['auth', 'database', 'typerror'])."
                        }
                    },
                    "required": ["code", "outcome"]
                }
            },
            "query_associative_memory": {
                "name": "query_associative_memory",
                "description": "Searches stored code patterns using Fly-LSH sparse binary Hamming similarity.",
                "annotations": {
                    "readOnlyHint": True,
                    "openWorldHint": False
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query_code": {
                            "type": "string",
                            "description": "The code query to search against associative memory."
                        },
                        "top_k": {
                            "type": "integer",
                            "default": 5,
                            "description": "Number of nearest neighbors to return."
                        }
                    },
                    "required": ["query_code"]
                }
            },
            "inspect_memory_state": {
                "name": "inspect_memory_state",
                "description": "Returns total active memories, synaptic weight distribution, and health statistics of the Mushroom Body.",
                "annotations": {
                    "readOnlyHint": True,
                    "openWorldHint": False
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            "reset_memory": {
                "name": "reset_memory",
                "description": "Resets or prunes the synaptic weights and associative memory back to baseline.",
                "annotations": {
                    "readOnlyHint": False,
                    "destructiveHint": True,
                    "idempotentHint": False,
                    "openWorldHint": False
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "confirm": {
                            "type": "boolean",
                            "description": "Must be set to true to confirm reset."
                        },
                        "backup": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to create a backup file before resetting."
                        }
                    },
                    "required": ["confirm"]
                }
            }
        }

    def get_all_tools(self) -> List[Dict[str, Any]]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)


calyx_tools_registry = CalyxToolRegistry()


def get_tool_schemas() -> List[Dict[str, Any]]:
    return calyx_tools_registry.get_all_tools()
