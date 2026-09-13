"""
Unit tests for Mushroom Body Dopamine Plasticity and Synaptic Bounds
"""
import pytest
import numpy as np
from calyx_mcp.memory import MushroomBodyMemory


@pytest.mark.asyncio
async def test_dopamine_reward_and_punishment(memory):
    code = "def execute_transaction(): pass"
    
    # 1. Initially pristine baseline (1.0)
    rep = memory.hasher.hash_code(code)
    assert np.allclose(memory.weights[rep.active_indices], 1.0)

    # 2. Apply punishment (-1.0)
    res_punish = await memory.remember(code, outcome="failure", error_message="Deadlock")
    assert res_punish["pattern_valence"] < 1.0
    assert memory.weights[rep.active_indices[0]] < 1.0

    # 3. Apply reward (+1.0)
    res_reward = await memory.remember(code, outcome="success")
    assert res_reward["pattern_valence"] > res_punish["pattern_valence"]


@pytest.mark.asyncio
async def test_synaptic_weight_clamping_bounds(memory):
    code = "def loop(): pass"
    
    # Repeat 100 punishments -> must not drop below min_weight (0.0)
    for _ in range(50):
        await memory.remember(code, outcome="failure")
    assert np.all(memory.weights >= memory.plasticity_cfg.min_weight)

    # Repeat 100 rewards -> must not exceed max_weight (5.0)
    for _ in range(50):
        await memory.remember(code, outcome="success")
    assert np.all(memory.weights <= memory.plasticity_cfg.max_weight)
