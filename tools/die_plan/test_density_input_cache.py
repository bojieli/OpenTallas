"""Density planning cache keys resolved geometry, not mutable Plan identities."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S
import taps as T


def plan():
    return SimpleNamespace(types={'x': {'outline_um': [300., 300.], 'hard_cores': [],
        'clock': {'tap_mode': 'density', 'tap_um': [80., 80.], 'sink_sites_um': [[80., 80., 1], [220., 220., 1]],
                  'tap_max_sinks': 1, 'tap_target_sinks': 1, 'tap_radius_um': 300., 'tap_refine_iters': 0}}},
        layers={r['name']: dict(r) for r in S.ASAP7_LAYERS},
        layer_budget=dict(S.DEFAULT_LAYER_BUDGET), grid=S.GRID_UM)


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    T._clear_density_cache()
    monkeypatch.setattr(T, 'planned_sinks', lambda *a, **kw: [])
    yield
    T._clear_density_cache()


def test_equivalent_transient_plans_reuse_planning_without_caller_alias(monkeypatch):
    a, b = plan(), plan()
    calls = []
    original = T._bisect
    def count(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(T, '_bisect', count)
    first = T.density_taps(a, 'x')
    expected = list(first)
    first.append(('caller-only', 0., 0., 0, 0.))
    assert T.density_taps(b, 'x') == expected
    assert len(calls) == 1
    assert all(isinstance(k, bytes) and len(k) == 32 for k in T._DENSITY_CACHE)


@pytest.mark.parametrize('change', ['clock', 'macro_origin', 'reserved', 'layer_grid', 'sink_inventory'])
def test_changed_actual_input_replans_same_object_and_matches_uncached(monkeypatch, change):
    p = plan()
    if change == 'macro_origin':
        p.types['x']['hard_cores'] = [{'inst': 'm', 'origin_um': [110., 110.], 'outline_um': [20., 20.]}]
    T.density_taps(p, 'x')
    if change == 'clock': p.types['x']['clock']['tap_um'] = [220., 220.]
    elif change == 'macro_origin': p.types['x']['hard_cores'][0]['origin_um'] = [60., 60.]
    elif change == 'reserved': p.types['x']['clock']['keepouts_um'] = [[60., 60., 100., 100.]]
    elif change == 'layer_grid': p.layers['M7']['offset_um'] += .01
    elif change == 'sink_inventory': p.types['x']['clock']['sink_sites_um'][0][0] = 120.
    original = T._bisect
    calls = []
    def count(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(T, '_bisect', count)
    changed = T.density_taps(p, 'x')
    assert len(calls) == 1
    T._clear_density_cache()
    assert T.density_taps(copy.deepcopy(p), 'x') == changed


def test_cache_payload_budget_excludes_oversized_results_and_evicts(monkeypatch):
    monkeypatch.setattr(T, '_DENSITY_CACHE_MAX_BYTES', 1000)
    monkeypatch.setattr(T, '_DENSITY_CACHE_MAX_ENTRIES', 2)
    for i in range(8):
        T._density_remember(bytes([i]) * 32, [('clk', float(i), 1., 1, 0.)])
    assert len(T._DENSITY_CACHE) <= 2
    assert T._DENSITY_CACHE_BYTES <= 1000
    T._density_remember(b'x' * 32, [('clk', 1., 1., 1, 0.)] * 100)
    assert b'x' * 32 not in T._DENSITY_CACHE
    assert T._DENSITY_CACHE_BYTES <= 1000
