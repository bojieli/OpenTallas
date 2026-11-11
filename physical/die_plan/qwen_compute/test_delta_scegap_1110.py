"""Tests for delta_scegap_1110 (DIE-QC-97 SC-EGAP: ft station rises out of the sc east gap)."""
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import delta_scegap_1110 as ev  # noqa: E402

CELL = [1.404, 0.27]


def _grp(x, y):
    return [[round(x - 2.16 * (k % 6), 4), round(y + 0.27 * (k // 6), 4)] for k in range(24)]


def _type():
    return {
        "outline_um": [613.44, 1339.2], "verilog_defines": ["OT_X"],
        "hard_cores": [{"inst": "u_core", "module": "m", "origin_um": [345.6, 648.0], "outline_um": [244.56, 514.08]}],
        "ft_slots": [
            {"name": "w2e", "in_face": "W", "out_face": "E", "out_window_um": [813.6, 916.2], "width": 24,
             "bit_site_cell_um": CELL, "regs_um": [[0.0, 841.6], [250.56, 613.44], [544.32, 639.36]],
             "bit_sites_um": [_grp(250.56, 613.44), _grp(544.32, 639.36)]},
            {"name": "col", "in_face": "N", "out_face": "S", "out_window_um": [285.0, 380.0], "width": 24,
             "bit_site_cell_um": CELL, "regs_um": [[384.6, 1339.2], [336.96, 1071.36]],
             "bit_sites_um": [_grp(336.96, 1071.36)]},
        ],
        "count_straps": [{"name": "s", "sites_um": [[100.0, 100.0]]}],
        "clock": {"landing_contract": {"bands": {"b": {"rect_um": [17.28, 800.0, 64.8, 900.0]}}}},
    }


@pytest.fixture
def moves(monkeypatch):
    m = {"t_a": (("w2e", 2, (544.32, 639.36), None),)}
    monkeypatch.setattr(ev, "MOVES", m)
    return m


def _plan():
    return {"die": {"name": "qwen_compute"}, "latency": {"lanes": {"a": 1}},
            "partition_types": {"t_a": _type(), "t_other": _type()}}


def test_moves_last_station_west_of_core_at_window_height(moves):
    raw0 = _plan()
    raw, rep = ev.apply(copy.deepcopy(raw0))
    f = raw["partition_types"]["t_a"]["ft_slots"][0]
    f0 = raw0["partition_types"]["t_a"]["ft_slots"][0]
    reg = f["regs_um"][2]
    assert abs(reg[0] - ev.X_TARGET) < 3 * ev.STEP and abs(reg[1] - (813.6 + 916.2) / 2) < 3 * ev.STEP
    dx, dy = reg[0] - 544.32, reg[1] - 639.36
    assert all(abs(p[0] - q[0] - dx) < 1e-6 and abs(p[1] - q[1] - dy) < 1e-6
               for p, q in zip(f["bit_sites_um"][1], f0["bit_sites_um"][1]))     # rigid move
    assert abs(dx / ev.SITE_X - round(dx / ev.SITE_X)) < 1e-6 and abs(dy / ev.SITE_Y - round(dy / ev.SITE_Y)) < 1e-6
    assert max(p[0] for p in f["bit_sites_um"][1]) + CELL[0] <= 345.6            # off the core
    assert rep[0]["reg_hop_max"][1] <= ev.KNEE_UM and rep[0]["bit_hop_max"][1] <= ev.KNEE_UM
    # only the moved station changed; other type, other slots, ports, latency byte-same
    t, t0 = copy.deepcopy(raw["partition_types"]["t_a"]), copy.deepcopy(raw0["partition_types"]["t_a"])
    for x in (t, t0):
        x["ft_slots"][0]["regs_um"][2] = None
        x["ft_slots"][0]["bit_sites_um"][1] = None
    assert t == t0
    assert raw["partition_types"]["t_other"] == raw0["partition_types"]["t_other"]
    assert raw["latency"] == raw0["latency"] and len(f["regs_um"]) == 3


def test_legalises_around_another_slots_sites(moves):
    raw = _plan()
    t = raw["partition_types"]["t_a"]
    tgt = (ev.X_TARGET, (813.6 + 916.2) / 2)
    t["ft_slots"][1]["bit_sites_um"].append(_grp(tgt[0] + 5, tgt[1]))          # sits on the target
    t["ft_slots"][1]["regs_um"].append([tgt[0] + 5, tgt[1]])
    raw, rep = ev.apply(raw)
    assert rep[0]["nudge_um"] != [0.0, 0.0]
    moved = raw["partition_types"]["t_a"]["ft_slots"][0]["bit_sites_um"][1]
    other = raw["partition_types"]["t_a"]["ft_slots"][1]["bit_sites_um"][-1]
    assert not any(ev._ov(ev._box(p, CELL), ev._box(q, CELL)) for p in moved for q in other)


def test_refuses_reapplication(moves):
    raw, _ = ev.apply(_plan())
    with pytest.raises(SystemExit, match="already applied"):
        ev.apply(raw)


def test_refuses_missing_slot_without_touching(moves):
    raw = _plan()
    raw["partition_types"]["t_a"]["ft_slots"].pop(0)
    before = json.dumps(raw)
    with pytest.raises(SystemExit, match="no ft slot"):
        ev.apply(raw)
    assert json.dumps(raw) == before


def test_refuses_when_hop_cannot_hold(moves):
    raw = _plan()
    f = raw["partition_types"]["t_a"]["ft_slots"][0]
    f["regs_um"][1] = [8.64, 100.0]                                               # previous station far below
    f["bit_sites_um"][0] = _grp(8.64, 100.0)
    with pytest.raises(SystemExit, match="no legal site group"):
        ev.apply(raw)


def test_cli_keeps_style(moves, tmp_path):
    src = tmp_path / "p.json"
    src.write_text(json.dumps(_plan(), separators=(",", ":")) + "\n")
    out = tmp_path / "o.json"
    sys.argv = ["x", str(src), str(out)]
    ev.main()
    b = out.read_bytes()
    assert b == (json.dumps(json.loads(b), separators=(",", ":")) + "\n").encode()
