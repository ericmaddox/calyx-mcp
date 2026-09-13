"""
Integration tests for atomic persistence and recovery
"""
import pytest
from calyx_mcp.memory import MushroomBodyMemory


@pytest.mark.asyncio
async def test_persistence_save_and_reload(temp_storage):
    code = "def persistent_func(): return True"
    
    # Instance 1: Learn a failure
    mem1 = MushroomBodyMemory(temp_storage.plasticity, temp_storage.storage)
    await mem1.remember(code, outcome="failure", error_message="Timeout")
    val1 = mem1.weights.copy()
    
    # Instance 2: Reload from disk
    mem2 = MushroomBodyMemory(temp_storage.plasticity, temp_storage.storage)
    assert len(mem2.records) == 1
    assert mem2.records[0]["error_message"] == "Timeout"
    assert (mem1.weights == mem2.weights).all()
