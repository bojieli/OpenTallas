"""RING-RESET-KEY 11-19 (FABLE-FIX-KV-PV): with reset.consumer_sites_um the reset tree keeps the relays of the plan the type
was bound on, so a landing ring must take its raw reset from the nearest FROZEN consumer site, not from the nearest clock tap
of a table that grew afterwards.  KV pv strict bind with 152-199 appended taps per type: 4 EMIT errors
"timed local wavefront reset relay rst_n_t<i> not found" (the nearest clock tap of those rings was an appended one).
    python3 -m pytest -q tools/die_plan/test_ring_reset_frozen.py"""
import copy

import pytest

import clock_landings as CL
import reset_tree as RT
import schema as S
from test_ring_reset_grid import physical_vehicle


def _body(n):
    body = "module b_mod (\n input wire clk,\n input wire [4:0] y\n);\n"
    for i in range(n):
        body += (f"wire rst_n_t{i}, p{i};\n"
                 f"ot_dp_rrelay u_rrl_{i} (.clk(clk), .d(p{i}), .q(rst_n_t{i}));\n")
    return body + "wire [4:0] y_q; assign y_q = y;\nendmodule\n"


def _appended(monkeypatch, grid):
    """the clock tap table after one tap was appended right at the N-face ring window (the reset tree's grid + 1)"""
    more = list(grid) + [("clk_t%d" % len(grid), 1.5, 796.0)]
    monkeypatch.setattr(RT, "_S_TAP_GRID", lambda P, tn: list(more))
    RT._TAPS.clear()
    CL._RING_PLAN.clear()
    return more


def test_ring_keeps_its_bound_relay_when_taps_are_appended_after_the_freeze(monkeypatch):
    p, t = physical_vehicle()
    grid = RT._taps(S.Plan(p), "B")
    c0 = CL.Landings(copy.deepcopy(p), t)
    c0.type_rtl("B", _body(len(grid)))
    before = c0.reset_placements["B"]["y"]                       # the relay the bound RTL uses
    assert before["net"] == "rst_n_t2"
    p["partition_types"]["B"].setdefault("reset", {})["consumer_sites_um"] = [[n, x, y] for n, x, y in grid]
    more = _appended(monkeypatch, grid)
    P = S.Plan(p)
    assert RT._clock_taps(P, "B") == more and len(RT._taps(P, "B")) == len(grid)       # 5 clock taps, 4 reset consumers
    assert CL.ring_taps(p, "B") == [(x, y) for _, x, y in grid]                         # the index space of rst_n_t<i>
    c = CL.Landings(p, t)
    out = c.type_rtl("B", _body(len(grid)))                      # the reset tree still emits 4 relays (frozen)
    after = c.reset_placements["B"]["y"]
    assert ".rst_n(rst_n_t2)" in out
    assert (after["net"], after["copied_raw_parent"], after["xy_um"]) == (before["net"], before["copied_raw_parent"], before["xy_um"])


def test_without_the_key_the_ring_follows_the_clock_taps(monkeypatch):
    p, t = physical_vehicle()
    grid = RT._taps(S.Plan(p), "B")
    more = _appended(monkeypatch, grid)
    assert "reset" not in p["partition_types"]["B"]
    assert CL.ring_taps(p, "B") == [(x, y) for _, x, y in more]  # no key: one table, the appended tap is a reset leaf too
    c = CL.Landings(p, t)
    out = c.type_rtl("B", _body(len(more)))
    assert ".rst_n(rst_n_t4)" in out and c.reset_placements["B"]["y"]["net"] == "rst_n_t4"
    c2 = CL.Landings(copy.deepcopy(p), t)
    CL._RING_PLAN.clear()
    with pytest.raises(CL.LandingError, match="rst_n_t4 not found"):
        c2.type_rtl("B", _body(len(grid)))                       # a body bound before the append has no such relay: fail closed
