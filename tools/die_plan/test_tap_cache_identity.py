"""Distinct transient plans must never share a tap result after an identity-key collision."""
from types import SimpleNamespace
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import taps as T


def plan(x):
    return SimpleNamespace(types={"x": dict(outline_um=[300., 300.], hard_cores=[],
        clock=dict(sink_sites_um=[[x, x, 1]], tap_radius_um=200, tap_max_sinks=1500))},
        clock=dict(insertion_ps=250), budgets={})


@pytest.mark.parametrize("mode", ["density", "sinks", "recentre"])
def test_colliding_identity_keys_recompute_distinct_plan_geometry(monkeypatch, mode):
    T._CACHE.clear()
    # Simulate CPython reusing an old plan's integer address without relying on allocator timing.
    monkeypatch.setattr(T, "id", lambda p: 17, raising=False)
    monkeypatch.setattr(T, "planned_sinks", lambda p, tn, *a, **kw: p.types[tn]["clock"]["sink_sites_um"])
    a, b = plan(40.), plan(240.)
    if mode == "density":
        call = lambda p: T.density_taps(p, "x")
    elif mode == "sinks":
        call = lambda p: T.sink_taps(p, "x")
    else:
        monkeypatch.setattr(T, "recentre_sinks", lambda p, tn: p.types[tn]["clock"]["sink_sites_um"])
        call = lambda p: T.recentre_displaced(p, "x", [("clk",150.,150.)], [(0,[0.,0.,300.,300.])])
    first = call(a)
    assert call(a) is first  # the same live plan retains the normal cache hit
    second = call(b)
    assert first != second
    assert abs(first[0][1] - second[0][1]) > 100
    assert call(a) == first
    assert any(value[0] is a for value in T._CACHE.values())
    T._CACHE.clear()
