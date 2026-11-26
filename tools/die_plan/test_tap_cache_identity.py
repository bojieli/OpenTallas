"""Distinct transient plans must never share a tap result after an identity-key collision."""
from types import SimpleNamespace
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import taps as T
import schema as S


def plan(x):
    return SimpleNamespace(types={"x": dict(outline_um=[300., 300.], hard_cores=[],
        clock=dict(sink_sites_um=[[x, x, 1]], tap_radius_um=200, tap_max_sinks=1500))},
        clock=dict(insertion_ps=250), budgets={},
        layers={r["name"]: dict(r) for r in S.ASAP7_LAYERS},
        layer_budget=dict(S.DEFAULT_LAYER_BUDGET), grid=S.GRID_UM)


@pytest.mark.parametrize("mode", ["density", "sinks", "recentre"])
def test_colliding_identity_keys_recompute_distinct_plan_geometry(monkeypatch, mode):
    T._CACHE.clear()
    T._clear_density_cache()
    # Simulate CPython reusing an old plan's integer address without relying on allocator timing.
    monkeypatch.setattr(T, "id", lambda p: 17, raising=False)
    monkeypatch.setattr(T, "planned_sinks", lambda p, tn, *a, **kw: p.types[tn]["clock"]["sink_sites_um"])
    # This test checks the process cache, independent of a warm fleet disk cache.
    monkeypatch.setenv("OT_BIND_GATE_CACHE", "off")
    a, b = plan(40.), plan(240.)
    if mode == "density":
        call = lambda p: T.density_taps(p, "x")
    elif mode == "sinks":
        call = lambda p: T.sink_taps(p, "x")
    else:
        monkeypatch.setattr(T, "recentre_sinks", lambda p, tn: p.types[tn]["clock"]["sink_sites_um"])
        call = lambda p: T.recentre_displaced(p, "x", [("clk",150.,150.)], [(0,[0.,0.,300.,300.])])
    first = call(a)
    again = call(a)
    assert again == first
    assert (again is not first) if mode == "density" else (again is first)
    second = call(b)
    assert first != second
    assert abs(first[0][1] - second[0][1]) > 100
    assert call(a) == first
    if mode == "density":
        assert T._DENSITY_CACHE  # immutable content keys retain no mutable Plan
    else:
        assert any(value[0] is a for value in T._CACHE.values())
    T._CACHE.clear()


def test_grid_sink_kmedians_vector_assignment_preserves_center_and_group_order(monkeypatch):
    pytest.importorskip("numpy")
    points = [(float(x), float(y)) for x in range(19) for y in range(15)]
    points.extend([(3.0, 2.0), (11.0, 13.0), (18.0, 14.0)])
    vector = T._kmedians(points, 13)
    monkeypatch.setitem(sys.modules, "numpy", None)
    assert T._kmedians(points, 13) == vector


def test_sink_tap_seed_prefix_matches_reseeding_each_candidate_count(monkeypatch):
    points = [(float(x), float(y), 1) for x in (60, 120, 180, 240) for y in (60, 120, 180, 240)]
    monkeypatch.setattr(T, "planned_sinks", lambda p, tn: points)
    kmedians = T._kmedians
    ks = []

    def fresh(pts, k, *, initial):
        ks.append(k)
        return kmedians(pts, k)

    a, b = plan(40.), plan(40.)
    for p in (a, b):
        p.types["x"]["clock"]["tap_radius_um"] = 35
    reused = T.sink_taps(a, "x")
    monkeypatch.setattr(T, "_kmedians", fresh)
    assert T.sink_taps(b, "x") == reused
    assert len(ks) > 1
    assert ks == list(range(ks[0], ks[-1] + 1))
