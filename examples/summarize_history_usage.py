"""Summarize fresh-session, paired history runs without inventing savings."""
import argparse
import json
from pathlib import Path


def total(row):
    usage = row.get('usage') or {}
    values = [usage.get(k) for k in ('input_tokens', 'output_tokens')]
    if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in values):
        return None
    cached = usage.get('cached_input_tokens')
    if cached is not None and (not isinstance(cached, int) or isinstance(cached, bool)
                               or not 0 <= cached <= values[0]):
        return None
    return sum(values)


def summarize(rows):
    pairs = {}
    seen_threads = set()
    for row in rows:
        key = row['task']
        arm = row['arm']
        if arm not in ('off', 'on') or arm in pairs.setdefault(key, {}):
            raise ValueError('Each task needs at most one run per arm; retain repeats separately')
        for thread in row.get('thread_ids', []):
            if thread in seen_threads:
                raise ValueError('Expected fresh sessions, not repeated cumulative counters')
            seen_threads.add(thread)
        pairs[key][arm] = row
    results = []
    for task, pair in pairs.items():
        eligible = set(pair) == {'off', 'on'}
        if eligible:
            off, on = pair['off'], pair['on']
            eligible = all(off.get(k) == on.get(k) and off.get(k) is not None
                           for k in ('model', 'effort', 'runtime_revision', 'corpus_size'))
            eligible = eligible and all(
                r.get('telemetry_valid') is True and r.get('protocol_compliant') is True
                and r.get('acceptance_passed') is True and r.get('exit_code') == 0
                and r.get('required_tool_calls') == 1 and r.get('mcp_calls') == 1
                and r.get('failed_mcp_calls') == 0 and r.get('unexpected_tool_calls') == 0
                and len(r.get('thread_ids', [])) == 1 and total(r) is not None
                for r in (off, on))
        totals = {arm: total(pair[arm]) if arm in pair else None for arm in ('off', 'on')}
        saved = totals['off'] - totals['on'] if eligible else None
        results.append({'task': task, 'eligible': bool(eligible), 'totals': totals,
                        'saved_tokens': saved,
                        'saved_percent': 100 * saved / totals['off'] if eligible and totals['off'] else None})
    return {'pairs': results,
            'accounting': 'input + output; cached input and reasoning output are subsets, not extra tokens',
            'scope': 'Warm synthetic history only; local pre-seeding is not agent learning. No price claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize([json.loads(line) for line in args.results.read_text().splitlines()
                                if line.strip()]), indent=2))
