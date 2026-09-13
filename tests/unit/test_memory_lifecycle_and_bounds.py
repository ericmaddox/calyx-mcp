"""
Unit tests for Memory Lifecycle, Ring Buffer Bounds, and Decay Dynamics.
"""
import pytest
import numpy as np
from calyx_mcp.memory import MushroomBodyMemory
from calyx_mcp.config import PlasticityConfig, StorageConfig


@pytest.mark.asyncio
async def test_bounded_memory_ring_buffer(tmp_path):
    # Setup storage config with small max_records
    storage_cfg = StorageConfig(storage_dir=str(tmp_path), max_records=10)
    plasticity_cfg = PlasticityConfig()
    mem = MushroomBodyMemory(plasticity_cfg=plasticity_cfg, storage_cfg=storage_cfg)

    # Ingest 25 memories
    for i in range(25):
        await mem.remember(f"def fn_{i}(): return {i}", outcome="success")

    # In-memory records must be strictly capped to max_records (10)
    assert len(mem.records) == 10
    assert mem.records[-1]["id"] == "rec_25"
    assert mem.records[0]["id"] == "rec_16"

    # Reload from disk and verify disk persistence matches
    mem_reloaded = MushroomBodyMemory(plasticity_cfg=plasticity_cfg, storage_cfg=storage_cfg)
    assert len(mem_reloaded.records) == 10
    assert mem_reloaded.records[-1]["id"] == "rec_25"
    assert mem_reloaded.records[0]["id"] == "rec_16"


@pytest.mark.asyncio
async def test_corrupt_file_graceful_recovery(tmp_path):
    storage_cfg = StorageConfig(storage_dir=str(tmp_path))
    plasticity_cfg = PlasticityConfig()

    # Create corrupt files
    corrupt_weights = tmp_path / storage_cfg.weights_filename
    corrupt_weights.write_bytes(b"CORRUPT_NON_NPZ_DATA")
    corrupt_meta = tmp_path / storage_cfg.metadata_filename
    corrupt_meta.write_text("{invalid_json: true", encoding="utf-8")

    mem = MushroomBodyMemory(plasticity_cfg=plasticity_cfg, storage_cfg=storage_cfg)
    # Memory must initialize to baseline rather than crashing
    assert mem.records == []
    assert np.allclose(mem.weights, 1.0)


@pytest.mark.asyncio
async def test_weight_decay_mechanism(tmp_path):
    storage_cfg = StorageConfig(storage_dir=str(tmp_path))
    plasticity_cfg = PlasticityConfig(decay_rate=0.8, enable_weight_decay=True)
    mem = MushroomBodyMemory(plasticity_cfg=plasticity_cfg, storage_cfg=storage_cfg)

    code = "def decay_target(): pass"
    # Reward once
    await mem.remember(code, outcome="success")
    rep = mem.hasher.hash_code(code)
    initial_elevated = float(np.mean(mem.weights[rep.active_indices]))
    assert initial_elevated > 1.0

    # Apply passive decay steps
    for _ in range(5):
        mem.apply_decay()

    # Verify weights on original pattern have decayed towards 1.0 baseline
    decayed = float(np.mean(mem.weights[rep.active_indices]))
    assert decayed < initial_elevated
    assert decayed > 1.0
