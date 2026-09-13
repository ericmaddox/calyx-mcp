"""
Unit tests for Contradiction Resolution & Ordering in Calyx MBON Reflex Engine.
Validates that recent failures take strict precedence over legacy rewards (Zero False Positives).
"""
import pytest
from calyx_mcp.reflex import ReflexDecisionEngine


@pytest.mark.asyncio
async def test_failure_overrides_multiple_prior_successes(reflex_engine, memory):
    code = "def process_transaction(user_id, amount):\n    return db.transfer(user_id, amount)"

    # 1. Simulate 5 consecutive successful test runs
    for _ in range(5):
        await memory.remember(code, outcome="success")

    # Verify synaptic valence is elevated
    state = await reflex_engine.evaluate_reflex(code)
    assert state.status == "safe"
    assert state.valence > 1.15

    # 2. Now simulate 1 runtime failure / bug (e.g. discovered concurrency issue)
    await memory.remember(
        code, 
        outcome="failure", 
        error_message="Deadlock detected in db.transfer under high concurrent load."
    )

    # 3. Evaluate reflex: Failure Override Rule MUST trigger 'avoid'
    post_failure_state = await reflex_engine.evaluate_reflex(code)
    assert post_failure_state.status == "avoid", (
        f"Expected 'avoid' after failure report, but got '{post_failure_state.status}'. "
        f"Valence was {post_failure_state.valence}, similarity {post_failure_state.similarity_with_past_bugs}"
    )
    assert post_failure_state.similarity_with_past_bugs >= 0.65
    assert "Deadlock detected" in post_failure_state.warning


@pytest.mark.asyncio
async def test_recency_sorting_tie_break(memory):
    code = "def authenticate(token):\n    return auth_service.verify(token)"

    # Store 3 successes then 1 failure
    for i in range(3):
        await memory.remember(code, outcome="success")
    await memory.remember(code, outcome="failure", error_message="Expired token bug")

    # Query similarity with top_k=2
    matches = await memory.query_similarity(code, top_k=2)
    assert len(matches) == 2
    # The most recent record (the failure) MUST be the first returned match due to recency tie-breaking
    assert matches[0]["outcome"] == "failure"
    assert matches[0]["error_message"] == "Expired token bug"


@pytest.mark.asyncio
async def test_punishment_then_reward_transition(reflex_engine, memory):
    code = "def parse_header(header_str):\n    return header_str.split(':')"

    # 1. Record 3 failures
    for _ in range(3):
        await memory.remember(code, outcome="failure", error_message="IndexError on malformed header")

    state = await reflex_engine.evaluate_reflex(code)
    assert state.status == "avoid"

    # 2. Apply fixed code with multiple rewards
    fixed_code = "def parse_header(header_str):\n    parts = header_str.split(':')\n    return (parts[0], parts[1]) if len(parts) > 1 else (parts[0], '')"
    for _ in range(4):
        await memory.remember(fixed_code, outcome="success")

    fixed_state = await reflex_engine.evaluate_reflex(fixed_code)
    assert fixed_state.status in ["safe", "neutral"]
