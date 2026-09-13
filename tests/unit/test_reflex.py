"""
Unit tests for MBON Reflex Decision Engine
"""
import pytest
from calyx_mcp.reflex import ReflexDecisionEngine


@pytest.mark.asyncio
async def test_reflex_status_transitions(memory, reflex_engine):
    code = "def delete_records(): db.drop_all()"

    # 1. Unseen code -> Neutral
    reflex_1 = await reflex_engine.evaluate_reflex(code)
    assert reflex_1.status == "neutral"
    assert reflex_1.warning is None

    # 2. Punish code -> Avoid reflex triggered
    await memory.remember(code, outcome="failure", error_message="Dropped production database!")
    reflex_2 = await reflex_engine.evaluate_reflex(code)
    assert reflex_2.status == "avoid"
    assert reflex_2.warning is not None
    assert "Dropped production database" in reflex_2.warning

    # 3. Reward safe code -> Safe reflex triggered
    safe_code = "def safe_delete(): db.archive_records()"
    for _ in range(3):
        await memory.remember(safe_code, outcome="success")
    reflex_3 = await reflex_engine.evaluate_reflex(safe_code)
    assert reflex_3.status == "safe"
