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


@pytest.mark.asyncio
async def test_hasher_config_mismatch_resets_with_backup(temp_storage):
    from pathlib import Path
    from calyx_mcp.config import HasherConfig

    code = "def sample_func(): return 42"
    # Instance 1: Default config (kenyon_cells=2048, active_k=102, seed=42)
    mem1 = MushroomBodyMemory(temp_storage.plasticity, temp_storage.storage)
    await mem1.remember(code, outcome="failure", error_message="Bug 1")
    assert len(mem1.records) == 1

    storage_dir = Path(temp_storage.storage.storage_dir)
    hasher_cfg_file = storage_dir / "hasher_config.json"
    assert hasher_cfg_file.exists()

    # Instance 2: Mismatched hasher config (kenyon_cells=1024, active_k=50, seed=999)
    mismatched_cfg = HasherConfig(kenyon_cells=1024, active_k=50, seed=999)
    mem2 = MushroomBodyMemory(
        temp_storage.plasticity,
        temp_storage.storage,
        hasher_cfg=mismatched_cfg
    )

    # Should detect mismatch, backup old weights/metadata/config, and reset state
    assert mem2.kenyon_dim == 1024
    assert len(mem2.weights) == 1024
    assert len(mem2.records) == 0  # Reset to clean baseline
    # Backup files should exist
    backups = list(storage_dir.glob("*.bak_*"))
    assert len(backups) >= 2

