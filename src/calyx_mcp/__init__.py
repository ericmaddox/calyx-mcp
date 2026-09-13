"""
Calyx MCP: Neuro-Symbolic Associative Code Memory MCP Server
Powered by the Drosophila Mushroom Body & Fly-LSH sparse memory architecture.
"""

__version__ = "1.0.0"
__author__ = "Calyx Research Team"

from .config import CalyxConfig, get_default_config
from .hasher import FlyLSHHasher, KenyonSparseRepresentation
from .memory import MushroomBodyMemory
from .reflex import ReflexDecisionEngine, ReflexOutcome
from .tools import CalyxToolRegistry, get_tool_schemas
from .server import CalyxMCPServer, create_mcp_server

__all__ = [
    "__version__",
    "CalyxConfig",
    "get_default_config",
    "FlyLSHHasher",
    "KenyonSparseRepresentation",
    "MushroomBodyMemory",
    "ReflexDecisionEngine",
    "ReflexOutcome",
    "CalyxToolRegistry",
    "get_tool_schemas",
    "CalyxMCPServer",
    "create_mcp_server",
]
