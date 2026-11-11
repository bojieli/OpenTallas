#!/usr/bin/env python3
"""STATION-DIR-1111 delta: swap + reverse on a listed chain, EQ asserts, idempotence guard, missing chain fails."""
import json
import sys
from pathlib import Path

import pytest

sys.path[:0] = [str(Path(__file__).resolve().parent)]
import delta_station_dir_1111 as M  # noqa: E402

TN, BUS = "col_h9_r0_p1__t1", "frame_int_o0"


def _type(regs, frm=(132.946, 1226.88), to=(1410.744, 673.89)):
    return {"outline_um": [1442.88, 1226.88],
            "buses": [{"name": BUS, "dir": "out", "face": "N", "width": 8}, {"name": "x_i", "dir": "in", "face": "E"}],
            "internal_stations": [
                {"conn": "bus:x_i", "from_um": [1442.88, 800.0], "to_um": [900.0, 800.0], "regs_um": [[1100.0, 800.0]],
                 "launch": "face bus x_i", "capture": "u_r0.u_cf.xi"},
                {"conn": "bus:" + BUS, "from_um": list(frm), "to_um": list(to), "regs_um": regs,
                 "launch": "u_r0.u_cf.rs", "capture": "face flop", "note": "n"}],
            "hard_cores": [{"inst": "u_r0.u_cf", "origin_um": [1300.0, 600.0]}]}


REGS = [[499.104, 1226.88], [865.261, 1226.88], [1231.419, 1226.88], [1410.744, 1040.048]]


@pytest.fixture
def chains(monkeypatch):
    monkeypatch.setattr(M, "CHAINS", {TN: (BUS,)})
    monkeypatch.setattr(M, "CHAINS_SUB", {})


def _plan(t):
    return json.dumps({"die": {"name": "s81"}, "partition_types": {TN: t, "other": {"outline_um": [1, 1]}}})


def test_reverse_and_eq(chains):
    out, rows = M.apply(_plan(_type([list(r) for r in REGS])))
    t = json.loads(out)["partition_types"][TN]
    e = t["internal_stations"][1]
    assert e["from_um"] == [1410.744, 673.89] and e["to_um"] == [132.946, 1226.88]
    assert e["regs_um"] == REGS[::-1]
    assert t["internal_stations"][0]["regs_um"] == [[1100.0, 800.0]]
    assert rows[0]["action"] == "REVERSED" and rows[0]["wire_um_out"] < rows[0]["wire_um_in"]


def test_text_style_kept_and_second_run_guard(chains):
    src = json.dumps(json.loads(_plan(_type([list(r) for r in REGS]))), indent=1)
    out, _ = M.apply(src)
    assert out.count("\n") == src.count("\n")           # values swapped in their own text
    with pytest.raises(SystemExit, match="already core -> face"):
        M.apply(out)
    out2, rows = M.apply(out, allow_fixed=True)
    assert out2 == out and rows[0]["action"] == "SKIP"


def test_resited_regs_are_reversed_by_name(chains):
    # a later stage re-sites the regs (and moves the entry): found by conn, whatever regs it carries are reversed
    regs = [[520.0, 1226.88], [900.0, 1226.88], [1250.0, 1226.88], [1410.744, 1000.0], [1410.744, 800.0]]
    t = _type(regs)
    t["internal_stations"].reverse()
    out, rows = M.apply(_plan(t))
    e = json.loads(out)["partition_types"][TN]["internal_stations"][0]
    assert e["regs_um"] == regs[::-1] and rows[0]["regs"] == 5


def test_missing_chain_fails(chains):
    t = _type([list(r) for r in REGS])
    t["internal_stations"].pop()
    with pytest.raises(SystemExit, match="0 internal_stations entries"):
        M.apply(_plan(t))


def test_labels_disagree_fails(chains):
    with pytest.raises(SystemExit, match="disagrees"):
        M.apply(_plan(_type([list(r) for r in REGS[::-1]])))
