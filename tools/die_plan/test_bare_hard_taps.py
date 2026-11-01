"""FLOW-20 11-01 (DIE-KV-60 01:21 ASK, COORD ruled): clock.tap_mode explicit / grid+explicit apply to a bare hard
wrapper (hard, no hard_cores); without tap_mode it keeps its ONE terminal at clock.tap_um (unchanged)."""
import json
from pathlib import Path
import schema
import taps
import die_clock


def raw(**ck):
    r = json.loads((Path(__file__).parent / "examples/tiny_plan.json").read_text())
    t = r["partition_types"]["src"]
    t["hard"] = True
    t["clock"].update(ck)
    return r


def src_ports(P):
    return sorted({port for part, port, *_ in die_clock.plan_taps(P) if P.parts[part]["type"] == "src"})


def test_bare_hard_default_one_terminal():
    P = schema.Plan(raw())
    assert schema.tap_grid(P, "src") == [("clk", 432.0, 432.0)]
    assert src_ports(P) == ["clk"]


def test_bare_hard_grid_explicit_feeds_every_entry(monkeypatch):
    monkeypatch.setattr(taps, "sink_sites", lambda P, tn, control=True: [(800., 120., 3.), (432., 840., 2.)])
    P = schema.Plan(raw(tap_mode="grid+explicit", tap_radius_um=200.,
                        added_taps=[dict(name="clk_t1", xy=[800., 120.]), dict(name="clk_t2", xy=[432., 820.])]))
    assert schema._grid_taps(P, "src") == [("clk", 432.0, 432.0)]        # the grid of a bare hard = its terminal
    got = schema.tap_grid(P, "src")
    assert [n for n, _, _ in got] == ["clk", "clk_t1", "clk_t2"]
    assert got[0][1:] == (432.0, 432.0) and got[1][1:] == (800.0, 120.0)
    assert src_ports(P) == ["clk", "clk_t1", "clk_t2"]


def test_bare_hard_explicit_feeds_every_entry(monkeypatch):
    monkeypatch.setattr(taps, "sink_sites", lambda P, tn, control=True: [(432., 432., 1.), (800., 120., 3.)])
    P = schema.Plan(raw(tap_mode="explicit", tap_radius_um=200.,
                        taps=[dict(name="clk", xy=[432., 432.]), dict(name="clk_t1", xy=[800., 120.])]))
    assert [n for n, _, _ in schema.tap_grid(P, "src")] == ["clk", "clk_t1"]
    assert src_ports(P) == ["clk", "clk_t1"]


def test_soft_type_grid_unchanged():
    r = raw()
    del r["partition_types"]["src"]["hard"]
    assert schema._grid_taps(schema.Plan(r), "src") == schema._grid_taps(
        schema.Plan(json.loads((Path(__file__).parent / "examples/tiny_plan.json").read_text())), "src")
