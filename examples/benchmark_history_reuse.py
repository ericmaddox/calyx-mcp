"""Bounded 100-lesson, three-task Calyx retrieval benchmark.

Runs one explicitly requested, billable Codex session. Preserve failed and
noncompliant attempts; only compare pairs that made the required real calls.
"""
import argparse, ast, asyncio, json, shutil, subprocess, sys, time
from pathlib import Path
TASKS = [{'id': 'cache-key', 'code': 'def cache_key(namespace, key): return key', 'lesson': 'Verified failure: cache keys collide across namespaces; return the namespaced tuple (namespace, key), preserving namespace first.'}, {'id': 'ceil-fee', 'code': 'def charge_units(total, quantum): return total // quantum', 'trained_code': 'def fee_units(amount, unit): return amount // unit', 'lesson': 'Verified failure: fee units must round up for partial units; use integer ceiling (amount + unit - 1) // unit.'}, {'id': 'inclusive-page', 'code': 'def slice_page(rows, first, last): return rows[first:last]', 'trained_code': 'def page(items, start, end): return items[start:end]', 'lesson': 'Verified failure: pagination end is inclusive; slice through end + 1 so the requested final item is retained.'}]

def validate_patch(code, task):
    try:
        t = ast.parse(code)
        allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Tuple, ast.Name, ast.Load, ast.Constant, ast.BinOp, ast.Add, ast.Sub, ast.FloorDiv, ast.Slice, ast.Subscript, ast.Load, ast.Index)
        if any((not isinstance(n, allowed) for n in ast.walk(t))) or len(t.body) != 1 or (not isinstance(t.body[0], ast.FunctionDef)):
            return False
        f = t.body[0]
        old = ast.parse(task['code']).body[0]
        if f.name != old.name or [a.arg for a in f.args.args] != [a.arg for a in old.args.args] or len(f.body) != 1 or (not isinstance(f.body[0], ast.Return)):
            return False
        if f.decorator_list or f.returns or f.args.defaults or f.args.vararg or f.args.kwarg or f.args.kwonlyargs or f.args.posonlyargs or any((a.annotation for a in f.args.args)):
            return False
        ns = {'__builtins__': {}}
        exec(compile(t, '<patch>', 'exec'), ns)
        fn = ns[f.name]
        if task['id'] == 'cache-key':
            return all(fn(n, k) == (n, k) for n, k in [('a', 'x'), ('b', 'x'), ('a', 'y')])
        if task['id'] == 'ceil-fee':
            cases = [(0, 10, 0), (1, 10, 1), (10, 10, 1), (11, 10, 2),
                     (19, 10, 2), (7, 3, 3), (14, 7, 2), (8, 1, 8)]
            return all(fn(amount, unit) == expected for amount, unit, expected in cases)
        return (fn(['a', 'b', 'c', 'd'], 1, 2) == ['b', 'c']
                and fn(['a', 'b'], 0, 0) == ['a']
                and fn([0, 1, 2, 3, 4], 2, 4) == [2, 3, 4])
    except (SyntaxError, TypeError, ValueError, NameError, KeyError, IndexError, ZeroDivisionError):
        return False

def build_lessons(path):
    lessons = [{'id': 'target-' + x['id'], 'code': x.get('trained_code', x['code']), 'lesson': x['lesson'], 'target': True} for x in TASKS]
    frozen = Path(__file__).with_name('history_lessons.json')
    if frozen.exists():
        distractors = json.loads(frozen.read_text(encoding='utf-8'))
        if len(distractors) != 97 or any((x.get('target') for x in distractors)):
            raise ValueError('frozen corpus must contain 97 distractors')
        lessons.extend(distractors)
        path.write_text(json.dumps(lessons, indent=2), encoding='utf-8')
        return lessons
    raise FileNotFoundError(f'frozen synthetic corpus missing: {frozen}')

def seed_calyx(repo, storage, lessons):
    sys.path.insert(0, str(repo / 'src'))
    from calyx_mcp.memory import MushroomBodyMemory
    from calyx_mcp.config import StorageConfig

    async def go():
        mem = MushroomBodyMemory(storage_cfg=StorageConfig(storage_dir=str(storage)))
        for x in lessons:
            await mem.remember(x['code'], 'failure', x['lesson'], ['synthetic', 'history', x['id']])
        return len(mem.records)
    return asyncio.run(go())

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--arm', choices=['off', 'on'], required=True)
    p.add_argument('--task', choices=[x['id'] for x in TASKS], required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--effort', required=True)
    p.add_argument('--order', choices=['on', 'off'], default='off')
    a = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    out = a.output.resolve() / a.arm / a.task
    out.mkdir(parents=True, exist_ok=False)
    corpus = build_lessons(out / 'lessons.json')
    notes = out / 'notes.json'
    notes.write_text(json.dumps(corpus), encoding='utf-8')
    storage = out / 'memory'
    began = time.monotonic()
    seeded = seed_calyx(repo, storage, corpus) if a.arm == 'on' else 0
    ingest = round(time.monotonic() - began, 3)
    records = []
    for task in [x for x in TASKS if x['id'] == a.task]:
        run = out / task['id']
        run.mkdir()
        schema = run / 'schema.json'
        schema.write_text(json.dumps({'type': 'object', 'properties': {'code': {'type': 'string'}}, 'required': ['code'], 'additionalProperties': False}), encoding='utf-8')
        prompt = 'Bounded synthetic repair trial. Do not inspect files, run shell commands, browse, delegate, or modify files. Deterministic acceptance tests cover valid inputs for this function. Repair this function using the verified project lesson available through the read-only history tool. Call the history tool exactly once with the buggy function as query and top_k=5, then return only the corrected function in code. Preserve name and parameters; use a pure expression with no imports, calls, decorators, or annotations. Code: ' + task['code']
        (run / 'prompt.txt').write_text(prompt, encoding='utf-8')
        cfg = {'model': a.model, 'model_reasoning_effort': a.effort, 'mcp_servers.node_repl.enabled': False}
        if a.arm == 'on':
            cfg.update({'mcp_servers.calyx_learned.command': sys.executable, 'mcp_servers.calyx_learned.args': ['-m', 'calyx_mcp.server'], 'mcp_servers.calyx_learned.env.PYTHONPATH': str(repo / 'src'), 'mcp_servers.calyx_learned.env.CALYX_STORAGE_DIR': str(storage), 'mcp_servers.calyx_learned.required': True, 'mcp_servers.calyx_learned.enabled_tools': ['query_associative_memory']})
        else:
            cfg.update({'mcp_servers.synthetic_history.command': sys.executable, 'mcp_servers.synthetic_history.args': [str(repo / 'examples' / 'history_search_server.py')], 'mcp_servers.synthetic_history.env.CALYX_HISTORY_NOTES': str(notes), 'mcp_servers.synthetic_history.required': True, 'mcp_servers.synthetic_history.enabled_tools': ['search_historical_lessons']})
        cmd = [shutil.which('codex'), 'exec', '--ephemeral', '--skip-git-repo-check', '--json', '--sandbox', 'read-only']
        for k, v in cfg.items():
            cmd += ['-c', k + '=' + json.dumps(v)]
        cmd += ['--output-schema', str(schema), '-o', str(run / 'answer.json'), '-']
        started = time.monotonic()
        with (run / 'events.jsonl').open('w', encoding='utf-8') as so, (run / 'stderr.log').open('w', encoding='utf-8') as se:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=so, stderr=se, cwd=run, text=True)
            proc.communicate(prompt)
        events = [json.loads(x) for x in (run / 'events.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
        usage = [e['usage'] for e in events if e.get('type') == 'turn.completed' and 'usage' in e]
        calls = [e['item'] for e in events if e.get('type') == 'item.completed' and e.get('item', {}).get('type') == 'mcp_tool_call']
        answer = json.loads((run / 'answer.json').read_text()) if (run / 'answer.json').exists() else {}
        returned = [c.get('result', {}) for c in calls]
        blob = json.dumps(returned).lower()
        retrieved = 'target-' + task['id'] in blob and task['lesson'].lower() in blob
        passed = validate_patch(answer.get('code', ''), task)
        tool_name = 'query_associative_memory' if a.arm == 'on' else 'search_historical_lessons'
        ids = [e.get('thread_id') for e in events if e.get('type') == 'thread.started']
        rec = {'arm': a.arm, 'task': task['id'], 'model': a.model, 'effort': a.effort, 'order': a.order, 'thread_ids': ids, 'elapsed_seconds': round(time.monotonic() - started, 3), 'acceptance_passed': passed, 'retrieval_target': retrieved, 'exit_code': proc.returncode, 'usage': usage[-1] if len(usage) == 1 else None, 'mcp_calls': len(calls), 'required_tool_calls': sum((c.get('tool') == tool_name for c in calls)), 'unexpected_tool_calls': sum((c.get('tool') != tool_name for c in calls)), 'failed_mcp_calls': sum((c.get('status') != 'completed' or bool(c.get('error')) for c in calls)), 'corpus_size': len(corpus), 'seeded_records': seeded, 'ingest_seconds': ingest}
        rec['infrastructure_valid'] = bool(not proc.returncode and rec['usage'] and (len(ids) == 1) and (rec['required_tool_calls'] == 1) and (not rec['unexpected_tool_calls']) and (not rec['failed_mcp_calls']))
        rec['protocol_compliant'] = bool(rec['required_tool_calls'] == 1 and not rec['unexpected_tool_calls'] and not rec['failed_mcp_calls'])
        rec['runtime_revision'] = revision
        rec['telemetry_valid'] = bool(not proc.returncode and len(usage) == 1 and len(ids) == 1
            and all(isinstance(usage[0].get(k), int) and not isinstance(usage[0][k], bool)
                    and usage[0][k] >= 0 for k in ('input_tokens', 'output_tokens'))
            and not any(e.get('type') in ('error', 'turn.failed') for e in events))
        rec['eligible'] = rec['telemetry_valid'] and rec['protocol_compliant'] and passed
        records.append(rec)
        (out / 'metrics.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
        print(json.dumps(rec), flush=True)
        if not rec['infrastructure_valid']:
            raise RuntimeError('incomplete or protocol-noncompliant run retained; stopping without retry')
    (out / 'aggregate.json').write_text(json.dumps({'arm': a.arm, 'records': records, 'corpus_size': len(corpus), 'seeded_records': seeded, 'ingest_seconds': ingest}, indent=2), encoding='utf-8')
if __name__ == '__main__':
    main()
