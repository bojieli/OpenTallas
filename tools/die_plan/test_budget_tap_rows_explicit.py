"""budget_tap_rows: an explicit-tap type whose R4 grid has no legal site still budgets its taps table (S81 t51 split)."""
import types

import pytest

import gen_phys as G


def _plan(mode):
    return types.SimpleNamespace(types={"t": {"clock": {"tap_mode": mode}}})


def _no_site(P, tn):
    raise ValueError("no legal clock tap site")


def test_explicit_without_legal_grid_site(monkeypatch):
    monkeypatch.setattr(G.S, "_grid_taps", _no_site)
    monkeypatch.setattr(G.S, "tap_grid", lambda P, tn: [("clk", 1.0, 2.0), ("clk_t1", 3.0, 4.0)])
    count, rows = G.budget_tap_rows(_plan("explicit"), "t")
    assert count == 0
    assert [r["name"] for r in rows] == ["clk", "clk_t1"]
    assert {r["kind"] for r in rows} == {"sinks"}


@pytest.mark.parametrize("mode", ["grid", "grid+explicit", "grid+sinks"])
def test_other_modes_still_refuse(monkeypatch, mode):
    monkeypatch.setattr(G.S, "_grid_taps", _no_site)
    monkeypatch.setattr(G.S, "tap_grid", lambda P, tn: [])
    with pytest.raises(ValueError):
        G.budget_tap_rows(_plan(mode), "t")


def test_explicit_with_legal_grid_unchanged(monkeypatch):
    monkeypatch.setattr(G.S, "_grid_taps", lambda P, tn: [("clk", 1.0, 2.0)])
    monkeypatch.setattr(G.S, "tap_grid", lambda P, tn: [("clk", 1.0, 2.0), ("clk_t1", 3.0, 4.0)])
    count, rows = G.budget_tap_rows(_plan("explicit"), "t")
    assert count == 1
    assert [r["kind"] for r in rows] == ["grid", "sinks"]
