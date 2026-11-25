import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leaf_grow as LG  # noqa: E402


def row():
    return {"outline_um": [1000.0, 800.0],
            "hard_cores": [{"inst": "a", "origin_um": [100.0, 100.0], "outline_um": [50.0, 50.0]},
                           {"inst": "b", "origin_um": [400.0, 300.0], "outline_um": [50.0, 50.0]}],
            "ft_slots": [{"name": "ft0", "in_face": "S", "out_face": "E", "in_window_um": [10.0, 90.0], "out_window_um": [10.0, 90.0],
                          "regs_um": [[50.0, 0.0], [60.0, 400.0], [1000.0, 50.0]],
                          "bit_sites_um": [[[50.0, 10.0], [52.0, 10.0]], [[1000.0, 50.0]]]}],
            "buses": [{"name": "x", "face": "N", "window_um": [200.0, 300.0]}],
            "internal_stations": [{"from_um": [120.0, 130.0], "to_um": [420.0, 330.0], "regs_um": [[250.0, 200.0]]}],
            "relay_sites": {"r": [30.0, 40.0], "s": [500.0, 500.0]},
            "clock": {"taps": [{"name": "t", "xy": [300.0, 300.0]}], "landing_contract": {"pins": [{"xy_um": [200.0, 800.0]}]},
                      "edge_clocks": [{"tap_um": [220.0, 790.0]}], "reach_fix_sinks": [[410.0, 310.0]]}}


def test_grow_shifts_cores_keeps_pins():
    g = LG.grow_row(row(), 100.0)
    assert g["outline_um"] == [1100.0, 800.0]
    assert [h["origin_um"] for h in g["hard_cores"]] == [[200.0, 100.0], [500.0, 300.0]]
    f = g["ft_slots"][0]
    assert f["regs_um"] == [[50.0, 0.0], [60.0, 400.0], [1100.0, 50.0]]           # E-face reg follows the face
    assert f["bit_sites_um"][0] == [[50.0, 10.0], [52.0, 10.0]] and f["bit_sites_um"][1] == [[1100.0, 50.0]]
    assert f["in_window_um"] == [10.0, 90.0] and g["buses"][0]["window_um"] == [200.0, 300.0]
    assert g["clock"]["landing_contract"]["pins"][0]["xy_um"] == [200.0, 800.0]
    assert g["clock"]["edge_clocks"][0]["tap_um"] == [220.0, 790.0]
    assert g["clock"]["taps"][0]["xy"] == [400.0, 300.0] and g["clock"]["reach_fix_sinks"] == [[510.0, 310.0]]
    assert g["internal_stations"][0]["regs_um"] == [[350.0, 200.0]]
    assert g["relay_sites"]["r"] == [30.0, 40.0] and g["relay_sites"]["s"] == [600.0, 500.0]


def test_invariants_pass_and_catch():
    r = row()
    g = LG.grow_row(r, 100.0)
    assert LG.check_rows(r, g) == []
    g["ft_slots"][0]["regs_um"].pop()
    assert any("register count" in b or "point set" in b for b in LG.check_rows(r, g))
    h = LG.grow_row(r, 100.0)
    h["outline_um"] = [1050.0, 800.0]
    assert any("INOUTLINE" in b for b in LG.check_rows(r, h))


def test_dy_moves_n_face_and_above_cut():
    g = LG.grow_row(row(), 0.0, 40.0, 250.0)
    assert g["outline_um"] == [1000.0, 840.0]
    assert [h["origin_um"] for h in g["hard_cores"]] == [[100.0, 100.0], [400.0, 340.0]]
    assert g["clock"]["landing_contract"]["pins"][0]["xy_um"] == [200.0, 840.0]
    assert LG.check_rows(row(), g) == []


def test_ft_interior_follows_cores():
    LG.FT_MODE[0] = "ft"
    try:
        g = LG.grow_row(row(), 100.0)
    finally:
        LG.FT_MODE[0] = True
    f = g["ft_slots"][0]
    assert f["regs_um"] == [[50.0, 0.0], [60.0, 400.0], [1100.0, 50.0]]          # x < xcut (100) stays; face points stay
    r = row(); r["ft_slots"][0]["regs_um"][1] = [300.0, 400.0]
    LG.FT_MODE[0] = "ft"
    try:
        g = LG.grow_row(r, 100.0)
    finally:
        LG.FT_MODE[0] = True
    assert g["ft_slots"][0]["regs_um"][1] == [400.0, 400.0]
    assert g["ft_slots"][0]["in_window_um"] == [10.0, 90.0]


def test_ft_xcut_keeps_street():
    r = row(); r["ft_slots"][0]["regs_um"][1] = [300.0, 400.0]
    LG.FT_MODE[0] = "ft"; LG.FT_XCUT[0] = 350.0
    try:
        g = LG.grow_row(r, 100.0)
    finally:
        LG.FT_MODE[0] = True; LG.FT_XCUT[0] = 0.0
    assert g["ft_slots"][0]["regs_um"][1] == [300.0, 400.0]


def test_ft_group_moves_whole():
    r = row(); r["ft_slots"][0]["bit_sites_um"][0] = [[300.0, 10.0], [360.0, 10.0]]   # straddles cut 350, centroid 330
    r["ft_slots"][0]["bit_sites_um"].append([[340.0, 200.0], [380.0, 200.0]])        # centroid 360 -> moves whole
    LG.FT_MODE[0] = "ft"; LG.FT_XCUT[0] = 350.0
    try:
        g = LG.grow_row(r, 100.0)
    finally:
        LG.FT_MODE[0] = True; LG.FT_XCUT[0] = 0.0
    b = g["ft_slots"][0]["bit_sites_um"]
    assert b[0] == [[300.0, 10.0], [360.0, 10.0]] and b[2] == [[440.0, 200.0], [480.0, 200.0]]
    assert b[1] == [[1100.0, 50.0]]


def test_raster_truncation_guard():
    r = row(); r["outline_um"] = [1442.88, 800.0]
    assert any("RASTER" in b for b in LG.check_rows(r, LG.grow_row(r, 120.96)))
    assert not any("RASTER" in b for b in LG.check_rows(r, LG.grow_row(r, 125.28)))
