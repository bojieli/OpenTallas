"""Tests for delta_sul1ctl_west_1111 (DIE-QC-97 SUL1CTL-WEST: sc x_su_l1_ctl column west, +1 station)."""
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import delta_sul1ctl_west_1111 as ev  # noqa: E402

CELL = [1.404, 0.27]


def _grp(x, y, n=24):
    return [[round(x - 2.16 * (k % 6), 4), round(y + 0.27 * (k // 6), 4)] for k in range(n)]


def _type():
    regs = [list(p) for p in ev.ORIG_REGS]
    return {
        "outline_um": [613.44, 1339.2],
        "hard_cores": [{"inst": "u_core", "module": "m", "origin_um": [345.6, 648.0], "outline_um": [244.56, 514.08]}],
        "ft_slots": [
            {"name": "x_su_l1_ctl", "in_face": "S", "out_face": "N", "out_window_um": [526.192, 604.448],
             "width": 23, "stations": 5, "layers": ["M7", "M5"], "bit_site_cell_um": CELL, "regs_um": regs,
             "bit_sites_um": [_grp(r[0], r[1]) for r in regs[1:]]},
            {"name": "other", "in_face": "W", "out_face": "E", "width": 23, "stations": 2, "bit_site_cell_um": CELL,
             "regs_um": [[0.0, 700.0], [100.0, 700.0]], "bit_sites_um": [_grp(100.0, 700.0)]},
        ],
        "count_straps": [{"name": "s", "sites_um": [[10.0, 10.0]]}],
        "clock": {"landing_contract": {"bands": {"b": {"rect_um": [391.408, 95.04, 470.688, 146.88]}}}},
    }


def _lat(c, st, pad=0):
    return {"cycles": c, "stations": st, "natural": c - pad, "pad": pad, "fixed": 0}


def _plan():
    lanes = {"sl_W0_su_l1__x_su_l1_ctl": _lat(19, 9), "sl_W0_su_l0__x_su_l0_ctl": _lat(19, 8, 1),
             "sl_E0_su_l1__x_su_l1_ctl": _lat(19, 9), "sl_E0_su_l0__x_su_l0_ctl": _lat(19, 8, 1),
             "sl_W0_x__other": _lat(4, 1)}
    return {"die": {"name": "qwen_compute"}, "latency": {"lanes": lanes},
            "latency_groups": [{"name": f"su_vmw_ctl_{s}", "kind": "bus",
                                "lanes": [f"sl_{s}_su_l0__x_su_l0_ctl", f"sl_{s}_su_l1__x_su_l1_ctl"]}
                               for s in ("W0", "E0")],
            "partitions": [{"name": "sl_W0_sc", "type": "t_a"}, {"name": "sl_E0_sc", "type": "t_other"}],
            "partition_types": {"t_a": _type(), "t_other": _type()}}


@pytest.fixture(autouse=True)
def one_type(monkeypatch):
    monkeypatch.setattr(ev, "TYPES", ("t_a",))


def test_moves_column_west_with_one_more_station():
    raw0 = _plan()
    raw, rep, lrep = ev.apply(copy.deepcopy(raw0))
    f = raw["partition_types"]["t_a"]["ft_slots"][0]
    f0 = raw0["partition_types"]["t_a"]["ft_slots"][0]
    assert f["stations"] == 6 and len(f["regs_um"]) == 6 and len(f["bit_sites_um"]) == 5
    assert f["regs_um"][0] == list(ev.ORIG_REGS[0])
    for reg, tgt, grp in zip(f["regs_um"][1:], ev.TARGETS, f["bit_sites_um"]):
        assert abs(reg[0] - tgt[0]) < 3 * ev.STEP and abs(reg[1] - tgt[1]) < 3 * ev.STEP
        dx, dy = reg[0] - ev.ORIG_REGS[1][0], reg[1] - ev.ORIG_REGS[1][1]
        assert all(abs(p[0] - q[0] - dx) < 1e-6 and abs(p[1] - q[1] - dy) < 1e-6
                   for p, q in zip(grp, f0["bit_sites_um"][0]))                 # rigid copy of the old S1 group
        assert abs(dx / ev.SITE_X - round(dx / ev.SITE_X)) < 1e-6
        assert abs(dy / ev.SITE_Y - round(dy / ev.SITE_Y)) < 1e-6
        assert max(p[0] for p in grp) + CELL[0] <= 345.6 or min(p[1] for p in grp) >= 1162.08   # off the core
        assert min(p[0] for p in grp) > 0 and max(p[0] for p in grp) < 590.16                # out of the east gap
    assert all(p["reg_hop"] <= ev.KNEE_UM and p["bit_hop_max"] <= ev.KNEE_UM for p in rep[0]["placed"])
    # latency: the moved slice's su_l1 lane +1, its su_l0 group partner pad +1; other slices / lanes unchanged
    L, L0 = raw["latency"]["lanes"], raw0["latency"]["lanes"]
    assert L["sl_W0_su_l1__x_su_l1_ctl"] == dict(L0["sl_W0_su_l1__x_su_l1_ctl"], cycles=20, stations=10, natural=20)
    assert L["sl_W0_su_l0__x_su_l0_ctl"] == dict(L0["sl_W0_su_l0__x_su_l0_ctl"], cycles=20, pad=2)
    for k in ("sl_E0_su_l1__x_su_l1_ctl", "sl_E0_su_l0__x_su_l0_ctl", "sl_W0_x__other"):
        assert L[k] == L0[k]
    assert [r["lane"] for r in lrep] == ["sl_W0_su_l1__x_su_l1_ctl"]
    # only the slot's regs / sites / stations / note changed
    t, t0 = copy.deepcopy(raw["partition_types"]["t_a"]), copy.deepcopy(raw0["partition_types"]["t_a"])
    for x in (t, t0):
        for k in ("regs_um", "bit_sites_um", "stations", "note"):
            x["ft_slots"][0].pop(k, None)
    assert t == t0
    assert raw["partition_types"]["t_other"] == raw0["partition_types"]["t_other"]
    assert raw["latency_groups"] == raw0["latency_groups"] and raw["partitions"] == raw0["partitions"]


def test_legalises_around_another_slots_sites():
    raw = _plan()
    t = raw["partition_types"]["t_a"]
    tgt = ev.TARGETS[1]
    t["ft_slots"][1]["bit_sites_um"].append(_grp(tgt[0] + 1, tgt[1] + 0.3))      # sits on station 2's target
    t["ft_slots"][1]["regs_um"].append([tgt[0] + 1, tgt[1] + 0.3])
    t["ft_slots"][1]["stations"] = 3
    raw, rep, _ = ev.apply(raw)
    assert rep[0]["placed"][1]["nudge_um"] != [0.0, 0.0]
    new = raw["partition_types"]["t_a"]["ft_slots"][0]["bit_sites_um"][1]
    other = raw["partition_types"]["t_a"]["ft_slots"][1]["bit_sites_um"][-1]
    assert not any(ev._ov(ev._box(p, CELL), ev._box(q, CELL)) for p in new for q in other)


def test_refuses_reapplication():
    raw, _, _ = ev.apply(_plan())
    with pytest.raises(SystemExit, match="already applied"):
        ev.apply(raw)


def test_refuses_unaligned_group_without_touching():
    raw = _plan()
    raw["latency"]["lanes"]["sl_W0_su_l0__x_su_l0_ctl"]["cycles"] = 18
    before = json.dumps(raw)
    with pytest.raises(SystemExit, match="not aligned"):
        ev.apply(raw)
    assert json.dumps(raw) == before


def test_refuses_missing_type(monkeypatch):
    monkeypatch.setattr(ev, "TYPES", ("t_a", "t_missing"))
    with pytest.raises(SystemExit, match="lacks sc types"):
        ev.apply(_plan())


def test_refuses_when_no_site_under_the_knee(monkeypatch):
    monkeypatch.setattr(ev, "TARGETS", ev.TARGETS[:1] + ((180.0, 900.0),) + ev.TARGETS[2:])   # 625 um from S1
    with pytest.raises(SystemExit, match="no legal site group"):
        ev.apply(_plan())


def test_cli_keeps_style(tmp_path):
    src = tmp_path / "p.json"
    src.write_text(json.dumps(_plan(), separators=(",", ":")) + "\n")
    out = tmp_path / "o.json"
    ev.main([str(src), str(out), "--no-verify"])
    b = out.read_bytes()
    assert b == (json.dumps(json.loads(b), separators=(",", ":")) + "\n").encode()
    assert json.loads(b)["partition_types"]["t_a"]["ft_slots"][0]["stations"] == 6
