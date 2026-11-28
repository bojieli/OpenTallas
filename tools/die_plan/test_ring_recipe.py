"""C-TAP-DENSITY-GROUPED-NOLEVER prerequisites (review of tap_cohort_assign --freeze-density, B1 + B2).
B1: with reset.consumer_sites_um a landing ring takes its reset relay from the frozen consumer sites in EVERY tap mode (explicit included),
    so an appended clock tap never names a relay rst_n_t<i> that does not exist.
B2: a density type frozen to explicit taps (clock.tap_recipe "density") keeps the density kit recipe.
    python3 -m pytest -q tools/die_plan/test_ring_recipe.py"""
import copy
import types

import clock_landings as CL
import gen_phys as G
import reset_tree as RT
import schema as S
from test_ring_reset_grid import physical_vehicle


def _more(monkeypatch, grid):
    more = list(grid) + [("clk_t%d" % len(grid), 1.5, 796.0)]
    monkeypatch.setattr(RT, "_S_TAP_GRID", lambda P, tn: list(more))
    RT._TAPS.clear()
    CL._RING_PLAN.clear()
    return more


def b1_check(mod, monkeypatch):
    p, t = physical_vehicle()
    grid = RT._taps(S.Plan(p), "B")
    ck = p["partition_types"]["B"]["clock"]
    ck["tap_mode"] = "explicit"
    ck["taps"] = [dict(name=n, xy=[x, y]) for n, x, y in grid]            # an explicit table, no kind 'core' entry
    p["partition_types"]["B"].setdefault("reset", {})["consumer_sites_um"] = [[n, x, y] for n, x, y in grid]
    more = _more(monkeypatch, grid)
    ck["taps"] = [dict(name=n, xy=[x, y]) for n, x, y in more]            # one tap appended after the freeze
    assert mod.ring_taps(p, "B") == [(x, y) for _, x, y in grid]           # the frozen index space, not the 5-entry clock table


def test_b1_explicit_type_follows_the_frozen_consumer_sites(monkeypatch):
    b1_check(CL, monkeypatch)


def test_b1_explicit_without_the_key_is_unchanged(monkeypatch):
    p, t = physical_vehicle()
    grid = RT._taps(S.Plan(p), "B")
    more = _more(monkeypatch, grid)
    ck = p["partition_types"]["B"]["clock"]
    ck["tap_mode"] = "explicit"
    ck["taps"] = [dict(name=n, xy=[x, y]) for n, x, y in more]
    assert "reset" not in p["partition_types"]["B"] or not p["partition_types"]["B"]["reset"].get("consumer_sites_um")
    assert CL.ring_taps(p, "B") == [(x, y) for _, x, y in more]            # no key: the clock table, as before


def _t(**ck):
    return {"clock": ck}


def test_b2_frozen_density_keeps_the_density_recipe():
    frozen = _t(tap_mode="explicit", tap_recipe="density", tap_radius_um=200.0)
    assert G._density(frozen) and G._density(_t(tap_mode="density"))
    assert not G._density(_t(tap_mode="explicit")) and not G._density(_t(tap_mode="explicit", tap_recipe="other"))
    assert G._density_cfg(frozen) == ["export OT_TAP_REASSIGN_UM = 200", "export OT_TAP_GRT_MODE = grt_report"]
    assert G._density_cfg(_t(tap_mode="explicit")) == []
    rows = G.budget_tap_rows(types.SimpleNamespace(types={"t": frozen}), "t") if False else None


def test_b2_budget_rows_and_cap_follow_the_recipe(monkeypatch):
    monkeypatch.setattr(G.S, "tap_grid", lambda P, tn: [("clk", 1.0, 2.0), ("clk_t1", 3.0, 4.0)])
    monkeypatch.setattr(G.S, "_grid_taps", lambda P, tn: [("clk", 1.0, 2.0)])
    P = types.SimpleNamespace(types={"t": _t(tap_mode="explicit", tap_recipe="density")})
    count, rows = G.budget_tap_rows(P, "t")
    assert count == 0 and {r["kind"] for r in rows} == {"density"}
    P2 = types.SimpleNamespace(types={"t": _t(tap_mode="explicit")})
    count, rows = G.budget_tap_rows(P2, "t")
    assert {r["kind"] for r in rows} == {"grid", "sinks"}


def test_schema_accepts_the_recipe_marker():
    props = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert props["tap_recipe"] == {"enum": ["density"]}


def _load(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _mutant(fname, old, new, name):
    from pathlib import Path
    import tempfile
    here = Path(__file__).resolve().parent
    src = (here / fname).read_text()
    assert old in src, (fname, old)
    d = Path(tempfile.mkdtemp())
    f = d / (name + ".py")
    f.write_text(src.replace(old, new, 1))
    return _load(f, name)


def test_mutants_are_killed(monkeypatch):
    import pytest
    m = _mutant("clock_landings.py", '        bool(plan["partition_types"][tn].get("reset", {}).get("consumer_sites_um"))', '        False', "clock_landings_mut")
    b1_check(CL, monkeypatch)                                              # control: the real module passes
    with pytest.raises(AssertionError):
        b1_check(m, monkeypatch)
    g = _mutant("gen_phys.py", 'return ck.get("tap_mode") == "density" or ck.get("tap_recipe") == "density"', 'return ck.get("tap_mode") == "density"', "gen_phys_mut")
    frozen = _t(tap_mode="explicit", tap_recipe="density", tap_radius_um=200.0)
    assert G._density(frozen)
    assert not g._density(frozen)                                          # the mutant loses the recipe: the B2 assertion would fail
