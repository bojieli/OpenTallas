"""FABLE-FIX-S81-BANKLEAF 11-18: read_loop_place moves the ROM of an over-reach read loop to the nearest legal site"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import read_loop_place as P
import relay_depth as RD


def _pins(hc, plan_dir):
    x, y = hc["origin_um"]
    if hc["module"].startswith("ot_rom"):
        return {"addr_in": {"0": (x + 10, y)}, "ce_in": {"0": (x + 10, y)}, "rd_out": {"0": (x + 10, y)}}
    return {"a": {"0": (x, y + 35)}, "ce5": {"0": (x, y + 35)}, "q5": {"0": (x, y + 40)}}


def _type(rom_x):
    return {"outline_um": [1000.0, 400.0], "hard_cores": [
        dict(inst="u_s8", module="ot_s81_cfg7_seq", origin_um=[600.0, 100.0], outline_um=[17.28, 51.84]),
        dict(inst="u_c8_5", module="ot_rom_4096x72_m8", origin_um=[rom_x, 100.0], outline_um=[38.04, 62.952]),
        dict(inst="u_wall", module="core", origin_um=[rom_x + 43.2, 60.0], outline_um=[300.0, 200.0])]}


def test_nearest_legal_site(monkeypatch):
    monkeypatch.setattr(RD, "_pin_table", _pins)
    t = _type(200.0)                                   # rd_out -> q5: 390 + 40 = 430 um; a wall right of the ROM blocks +x
    m = P.place(t, "u_s8", "u_c8_5", None)
    assert m and max(m["after_um"]) <= P.LIMIT - P.MARGIN and max(m["before_um"]) == 430.0
    assert m["move_um"][0] == 0.0 and m["move_um"][1] > 0          # the wall leaves only the y move
    box = P._box(dict(t["hard_cores"][1], origin_um=m["new_origin_um"]))
    assert P._legal(t, dict(t["hard_cores"][1], origin_um=m["new_origin_um"]), [P._box(h) for h in t["hard_cores"] if h["inst"] != "u_c8_5"])
    assert box[1] >= P.EDGE_UM


def test_no_site_is_none(monkeypatch):
    monkeypatch.setattr(RD, "_pin_table", _pins)
    monkeypatch.setattr(P, "RADIUS_UM", 20.0)
    assert P.place(_type(100.0), "u_s8", "u_c8_5", None) is None
