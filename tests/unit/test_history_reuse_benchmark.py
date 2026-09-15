import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('history', Path(__file__).resolve().parents[2] / 'examples' / 'benchmark_history_reuse.py')
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)

def test_target_fixes_and_known_bad_candidates():
    for task in history.TASKS:
        assert not history.validate_patch(task['code'], task)
    assert history.validate_patch('def cache_key(namespace, key): return (namespace, key)', history.TASKS[0])
    assert history.validate_patch('def charge_units(total, quantum): return (total + quantum - 1) // quantum', history.TASKS[1])
    assert history.validate_patch('def slice_page(rows, first, last): return rows[first:last + 1]', history.TASKS[2])

def test_rejects_wrong_contracts_and_unsafe_ast():
    assert not history.validate_patch('def cache_key(namespace, key): return (key, namespace)', history.TASKS[0])
    assert not history.validate_patch('def charge_units(total, quantum): return round(total / quantum)', history.TASKS[1])
    assert not history.validate_patch("def slice_page(rows, first, last): return eval('rows')", history.TASKS[2])

def test_corpus_has_targets_and_coherent_distractors(tmp_path):
    lessons = history.build_lessons(tmp_path / 'lessons.json')
    assert len(lessons) == 100 and sum((x['target'] for x in lessons)) == 3
    assert len({x['lesson'] for x in lessons}) == len(lessons)


def test_rejects_overfitting_one_test_value():
    assert not history.validate_patch("def cache_key(namespace, key): return (namespace, 'x')", history.TASKS[0])
    assert not history.validate_patch("def charge_units(total, quantum): return (total + 9) // 10", history.TASKS[1])
