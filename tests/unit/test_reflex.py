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


@pytest.mark.asyncio
async def test_loss_asymmetry_boundaries(memory, reflex_engine):
    """
    Calyx is loss-averse by design:
    - 1 failure -> avoid (0.775 < 0.85)
    - 1 success -> neutral (1.15 is not > 1.15)
    - 2 successes -> safe (1.3225 > 1.15)
    """
    # 1 failure -> avoid (< 0.85)
    bad_code = "def parse_bad_token(tok): return eval(tok)"
    await memory.remember(bad_code, outcome="failure", error_message="RCE via eval")
    res_bad = await reflex_engine.evaluate_reflex(bad_code)
    assert res_bad.status == "avoid"
    assert res_bad.valence < 0.85

    # 1 success -> neutral (<= 1.15 safe ceiling)
    good_code = "def parse_good_token(tok): return json.loads(tok)"
    await memory.remember(good_code, outcome="success")
    res_good_1 = await reflex_engine.evaluate_reflex(good_code)
    assert res_good_1.status == "neutral"
    assert res_good_1.valence <= 1.15

    # 2 successes -> safe (> 1.15 safe ceiling)
    await memory.remember(good_code, outcome="success")
    res_good_2 = await reflex_engine.evaluate_reflex(good_code)
    assert res_good_2.status == "safe"
    assert res_good_2.valence > 1.15


@pytest.mark.asyncio
async def test_contradiction_guard_with_warning(memory):
    """
    When code has positive valence (> 1.15) but >= contradiction_guard_similarity with a past failure,
    the contradiction guard returns 'neutral' with a warning instead of falsely claiming 'safe'.
    """
    from calyx_mcp.config import ReflexConfig

    engine = ReflexDecisionEngine(memory, reflex_cfg=ReflexConfig(contradiction_guard_similarity=0.40))
    bug_code = "def query_db(uid): return db.find(f'SELECT * FROM u WHERE id={uid}')"
    fix_code = "def query_db(uid): return db.find('SELECT * FROM u WHERE id=%s', uid)"

    await memory.remember(bug_code, outcome="failure", error_message="SQL Injection")
    # Reward fix multiple times to get high valence
    for _ in range(3):
        await memory.remember(fix_code, outcome="success")

    res = await engine.evaluate_reflex(fix_code)
    # Because fix shares similarity with bug, contradiction guard triggers neutral
    assert res.status == "neutral"
    assert res.warning is not None
    assert "Mixed history detected" in res.warning


@pytest.mark.asyncio
async def test_configurable_reflex_thresholds(memory):
    """
    Verify that custom ReflexConfig thresholds change decision engine behavior.
    """
    from calyx_mcp.config import ReflexConfig

    # Lower safe ceiling to 1.10 so a single reward (1.15) reaches 'safe'
    custom_cfg = ReflexConfig(safe_valence_ceiling=1.10)
    engine = ReflexDecisionEngine(memory, reflex_cfg=custom_cfg)

    code = "def fast_compute(x): return x * 2"
    await memory.remember(code, outcome="success")

    res = await engine.evaluate_reflex(code)
    assert res.status == "safe"
    assert res.valence == 1.15

