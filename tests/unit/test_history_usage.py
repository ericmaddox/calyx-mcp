import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('usage', Path(__file__).resolve().parents[2] / 'examples/summarize_history_usage.py')
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)


def row(arm, input_tokens):
    return dict(task='repair', arm=arm, model='same', effort='medium', runtime_revision='same',
                corpus_size=100, thread_ids=[arm], telemetry_valid=True, protocol_compliant=True,
                acceptance_passed=True, exit_code=0, mcp_calls=1, required_tool_calls=1,
                failed_mcp_calls=0, unexpected_tool_calls=0,
                usage=dict(input_tokens=input_tokens, output_tokens=10, cached_input_tokens=80))


def test_negative_savings_do_not_double_count_cached_tokens():
    result = usage.summarize([row('off', 100), row('on', 150)])['pairs'][0]
    assert result['eligible'] and result['saved_tokens'] == -50


def test_pretend_call_and_mismatched_models_are_ineligible():
    off, on = row('off', 100), row('on', 150)
    off['mcp_calls'] = 0
    assert usage.summarize([off, on])['pairs'][0]['saved_tokens'] is None
    off['mcp_calls'] = 1
    on['model'] = 'different'
    assert not usage.summarize([off, on])['pairs'][0]['eligible']


def test_bad_telemetry_and_reused_session_rejected():
    off, on = row('off', 100), row('on', 150)
    on['usage']['cached_input_tokens'] = 151
    assert usage.summarize([off, on])['pairs'][0]['saved_tokens'] is None
    on['thread_ids'] = off['thread_ids']
    with pytest.raises(ValueError, match='fresh sessions'):
        usage.summarize([off, on])
