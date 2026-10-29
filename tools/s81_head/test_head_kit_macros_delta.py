"""DIE-HEAD-21 HK2: head_kit_macros_delta.py unit tests (synthetic plan, no EDA tools)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_kit_macros_delta as D  # noqa: E402

BIG, SMALL = D.BIG, D.SMALL


def lane_insts(pref):
    big = [(f"{pref}u_ep.g_fifo_safe.u_m.g_bank[{i}].u_m", BIG) for i in range(36)]
    small = [(f"{pref}u_gb.u_sf.g_bank[{i}].u_m", SMALL) for i in range(19)]
    return big + small


def test_lane_block_shape_and_no_overlap():
    rel = D.lane_block(lane_insts("u_core.u_la."))
    assert len(rel) == 55 and len({r[0] for r in rel}) == 55
    size = {BIG: D.lef_size(D.macro_paths(BIG)["lef"]), SMALL: D.lef_size(D.macro_paths(SMALL)["lef"])}
    rs = [(dx, dy, dx + size[m][0], dy + size[m][1]) for _, m, dx, dy in rel]
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            assert not D.ov(rs[i], rs[j], D.XGAP, D.YGAP)
    for _, _, dx, dy in rel:                     # on the 8.64 hard-core lattice
        assert abs(dx / D.G - round(dx / D.G)) < 1e-6 and abs(dy / D.G - round(dy / D.G)) < 1e-6


def test_lane_block_rejects_other_sets():
    try:
        D.lane_block(lane_insts("x.")[:-1])
    except ValueError:
        return
    raise AssertionError("54-macro set accepted")


def test_place_lane_avoids_band_and_stays_near_window():
    size = {BIG: D.lef_size(D.macro_paths(BIG)["lef"]), SMALL: D.lef_size(D.macro_paths(SMALL)["lef"])}
    rel = D.lane_block(lane_insts("u_core.u_lb."))
    ko = [((17.28 - 8.64, 120.0 - 8.64, 30.24 + 8.64, 326.0 + 8.64), "band:coll_ib")]
    got = D.place_lane(rel, size, "W", 120.0, 547.2, 1442.88, 1226.88, ko, [])
    assert got
    xs = [x for _, _, x, _ in got]
    ys = [y for _, _, _, y in got]
    assert min(xs) >= 38.88 and min(xs) < 60          # just past the band halo, at the W face
    assert min(ys) < 547.2 and max(ys) > 120.0          # overlaps the window span


def test_pins_from_lef(tmp_path):
    pf, n = D.write_pins(BIG, D.macro_paths(BIG)["lef"], tmp_path)
    doc = json.loads((tmp_path / pf).read_text())
    assert n > 100 and doc["module"] == BIG
    assert all(p["layer"] != "M1" and p["name"] not in ("VDD", "VSS") for p in doc["pins"])


def test_move_reset_taps():
    t = {"outline_um": [100.0, 100.0], "reset": {"local_taps_um": [[50.0, 50.0], [10.0, 10.0]]}}
    mv = D.move_reset_taps(t, [(40.0, 40.0, 60.0, 60.0)])
    assert len(mv) == 1 and mv[0][0] == [50.0, 50.0]
    nx, ny = mv[0][1]
    assert not (40 - 4.32 < nx < 60 + 4.32 and 40 - 4.32 < ny < 60 + 4.32)
    assert t["reset"]["local_taps_um"][1] == [10.0, 10.0]
