import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('schedule', Path(__file__).resolve().parents[1] / 'tools/v41_l0_dependency_schedule.py')
schedule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schedule)


def test_unknown_duration_propagates_without_erasing_floor():
    r = schedule.solve([dict(id='a', after=[], floor=10, cycles=None), dict(id='b', after=['a'], floor=5, cycles=5)])
    assert r['b']['finish_floor'] == 15
    assert r['b']['finish_exact'] is None


def test_parallel_dependency_join_is_max_not_sum():
    r = schedule.solve([dict(id='a', after=[], floor=10, cycles=10), dict(id='b', after=[], floor=6, cycles=6), dict(id='c', after=['a','b'], floor=3, cycles=3)])
    assert r['c']['finish_exact'] == 13


def test_layer0_dimensions_and_fixture_do_not_become_rate():
    d = schedule.build()
    assert d['current_known_issue_floor'] == 2560
    assert d['transferred_fixture_floor'] == 11776
    assert d['actual_attention_path_cycles'] is None
    assert d['engine_fixture']['T128']['qk_accept_window'] == 32
    assert d['engine_fixture']['T640']['qk_accept_window'] == 160
    assert d['window_candidate']['saved_cycles'] == 177
