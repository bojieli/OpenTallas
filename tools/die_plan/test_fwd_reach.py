"""KV-PLAN-R2 11-20: fwd_reach.py checks the hops of DECLARED forward-leg stations, not only their presence."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fwd_reach as F  # noqa: E402


class FakePlan:
    def __init__(self, stations):
        self.lanes = {"L1": {"note": "tap_tree serdes.tx_up"}, "L2": {"note": "tap_tree serdes.tx_up"}}
        self.parts = {"p0": {"type": "t"}, "a": {"type": "x"}, "b": {"type": "x"}}
        self.ports = {"L1_0": {"src": {"part": "a", "bus": "o_up"}, "dst": {"part": "p0", "bus": "i_up"}},
                      "L2_0": {"src": {"part": "p0", "bus": "o_up"}, "dst": {"part": "b", "bus": "i_up"}}}
        self.types = {"t": {"outline_um": [2000.0, 1000.0], "internal_stations": stations}, "x": {"hard": True}}


def run(tmp_path, monkeypatch, stations, reach=300.0):
    monkeypatch.setattr(F.S, "Plan", lambda raw, path=None: FakePlan(stations))
    monkeypatch.setattr(F.C, "_bus_targets", lambda P, tn: {"i_up": ("E", (2000.0, 500.0)), "o_up": ("W", (0.0, 500.0))})
    plan = tmp_path / "plan.json"
    plan.write_text("{}")
    out = tmp_path / "out.json"
    rc = F.main([str(plan), "--json", str(out), "--reach", str(reach)])
    return rc, json.loads(out.read_text())["rows"]


def row(n):
    xs = [2000.0 - 2000.0 * k / (n + 1) for k in range(1, n + 1)]
    return {"conn": "bus:o_up", "from_um": [2000.0, 500.0], "to_um": [0.0, 500.0], "regs_um": [[x, 500.0] for x in xs]}


def test_undeclared_long_leg_fails(tmp_path, monkeypatch):
    rc, rows = run(tmp_path, monkeypatch, [])
    assert rc == 1 and rows[0]["verdict"] == "FAIL" and rows[0]["stations"] == 6


def test_declared_rows_with_long_hops_fail(tmp_path, monkeypatch):
    rc, rows = run(tmp_path, monkeypatch, [row(5)])          # 2000 / 6 = 333 um hops > 300
    assert rc == 1 and rows[0]["verdict"] == "FAIL"
    assert rows[0]["declared"] and rows[0]["declared_stations"] == 5 and rows[0]["declared_max_hop_um"] == pytest.approx(333.3, abs=0.1)


def test_declared_rows_within_reach_pass(tmp_path, monkeypatch):
    rc, rows = run(tmp_path, monkeypatch, [row(6)])          # 2000 / 7 = 286 um
    assert rc == 0 and rows[0]["verdict"] == "PASS" and rows[0]["declared_max_hop_um"] <= 300


def test_declared_row_without_geometry_fails(tmp_path, monkeypatch):
    rc, rows = run(tmp_path, monkeypatch, [{"conn": "bus:o_up", "regs_um": [[1000.0, 500.0]]}])
    assert rc == 1 and rows[0]["declared"] and rows[0]["declared_max_hop_um"] is None


def test_declared_max_hop_uneven():
    r = {"from_um": [0, 0], "regs_um": [[100, 0], [100, 350]], "to_um": [120, 350]}
    assert F.declared_max_hop(r) == 350
