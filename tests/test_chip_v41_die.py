"""Die-level V4.1 assembly: floorplan legality, edge binding, bundled views and record parsing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from chip_assembly import v41_corridor, v41_die  # noqa: E402


def overlap(a, b) -> float:
    return max(0.0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x)) * max(0.0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))


@pytest.mark.parametrize("arch,n_attn,n_coll", [("v41_rom", 1, 1), ("v41_hbm", 1, 1), ("v41_rom", 2, 2),
                                                 ("v41_hbm", 2, 2)])
def test_floorplan_is_legal_and_edges_bind(arch, n_attn, n_coll):
    m = v41_die.build(v41_die.Params(arch=arch, n_attn=n_attn, n_coll=n_coll))
    W, H = m["die_mm"]
    cl = m["clusters"]
    names = {c.inst for c in cl}
    assert len(names) == len(cl)
    for c in cl:
        assert c.x >= -1e-9 and c.y >= -1e-9 and c.x + c.w <= W + 1e-9 and c.y + c.h <= H + 1e-9, c.inst
    for i, a in enumerate(cl):
        for b in cl[i + 1:]:
            assert overlap(a, b) < 1e-9, (a.inst, b.inst)
    assert sum(c.kind == "tile" for c in cl) == 48
    for b in m["buses"]:
        assert b.src in names and b.dst in names and b.bits > 0
    # every tile is fed and returns; HBM comparator tiles also receive a weight stream
    tiles = [c.inst for c in cl if c.kind == "tile"]
    kinds = {b.id.split(".")[0] for b in m["buses"]}
    assert {"act", "res", "hbm_window", "idx_keys", "selected_kv"} <= kinds
    assert ("weights" in kinds) == (arch == "v41_hbm")
    for t in tiles:
        assert any(b.dst == t and b.id.startswith("act.") for b in m["buses"])
    # all tile slots fit (no overfill) in the reservation plan's compute regions
    assert all(s["fill"] < 1.0 for s in m["tile_slots"])


def test_ledger_widths_are_used():
    conn = {e["id"]: e for e in json.loads((ROOT / v41_die.INPUTS["connectivity"]).read_text())["edges"]}
    m = v41_die.build(v41_die.Params(arch="v41_rom"))
    act = next(b for b in m["buses"] if b.id.startswith("act."))
    assert act.bits == conn["vm_me"]["data_bits"] + conn["vm_he"]["data_bits"]
    cv = next(b for b in m["buses"] if b.id.startswith("coll_vm."))
    assert cv.bits == conn["collective_vm"]["data_bits"]


def test_bundled_case_writes(tmp_path):
    m = v41_die.build(v41_die.Params(arch="v41_hbm"))
    man = v41_die.write_case(m, tmp_path, 32, 7, 0.30, 0.25)
    assert man["bundle_nets"] == sum(v41_die.bundle_count(b.bits, 32) for b in m["buses"])
    tech = (tmp_path / "tech.lef").read_text()
    assert "PITCH 2.560" in tech  # M8 0.080 x 32
    lef = (tmp_path / "clusters.lef").read_text()
    assert lef.count("MACRO ") == len(m["clusters"])
    netlist = (tmp_path / "die.v").read_text()
    assert "module ot_v41d_die_v41_hbm" in netlist and "(* blackbox *)" not in netlist
    assert "die_empty.v" in (tmp_path / "run_base.tcl").read_text()


def test_parsers(tmp_path):
    (tmp_path / "wl.csv").write_text("tool net total_wl #pins\ngrt: n_act_x[0] 9699.24 2\ngrt: clk 5 2\n")
    assert v41_die.parse_wirelength(tmp_path / "wl.csv") == {"n_act_x[0]": 9699.24}
    (tmp_path / "u.txt").write_text("GRIDX 0,10\nGRIDY 0,10\nL M8 0 100.0/40.0 100.0/100.0\n")
    (tmp_path / "b.txt").write_text("GRIDX 0,10\nGRIDY 0,10\nL M8 0 100.0/30.0 100.0/100.0\n")
    cm = v41_die.congestion_map(tmp_path / "u.txt", tmp_path / "b.txt")
    assert cm["grid"]["M8"][0] == [round(10 / 70, 3), None]
    assert cm["summary"]["M8"]["windows_over_1"] == 0


def test_corridor_writes(tmp_path):
    man = v41_corridor.write(tmp_path, 3.4, 140.0, 30, [0.9, 1.118], 0.25, "M4", "M5")
    assert [g["stations"] for g in man["groups"]] == [3, 3]
    v = (tmp_path / "corridor.v").read_text()
    assert v.count(v41_corridor.FLOP) == 15 * 4 * 2
    assert "set_routing_layers -signal M4-M9" in (tmp_path / "run.tcl").read_text()
