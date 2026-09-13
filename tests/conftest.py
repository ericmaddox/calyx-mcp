"""
Shared pytest fixtures for Calyx MCP
"""
import pytest
from calyx_mcp.config import CalyxConfig
from calyx_mcp.hasher import FlyLSHHasher
from calyx_mcp.memory import MushroomBodyMemory
from calyx_mcp.reflex import ReflexDecisionEngine
from calyx_mcp.server import CalyxMCPServer


@pytest.fixture
def temp_storage(tmp_path):
    cfg = CalyxConfig()
    cfg.storage.storage_dir = str(tmp_path)
    return cfg


@pytest.fixture
def hasher():
    return FlyLSHHasher()


@pytest.fixture
def memory(temp_storage):
    return MushroomBodyMemory(
        plasticity_cfg=temp_storage.plasticity,
        storage_cfg=temp_storage.storage
    )


@pytest.fixture
def reflex_engine(memory):
    return ReflexDecisionEngine(memory)


@pytest.fixture
def server(temp_storage):
    return CalyxMCPServer(temp_storage)
