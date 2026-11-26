import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import suc_resite as S
import adv_fp_floorplan as fp


def _type():
    core = lambda n, x, y, w, h: {"inst": n, "origin_um": [x, y], "outline_um": [w, h], "orient": "R0"}
    return {"outline_um": [1000.0, 800.0],
            "hard_cores": [core("a", 100, 100, 300, 300), core("b", 600, 100, 300, 300)],
            "buses": [{"name": "x", "width": 100}],
            "internal_stations": [{"conn": "bus:x", "bits": 100, "launch": "core", "from_um": [50.0, 600.0], "to_um": [950.0, 600.0],
                                   "regs_um": [[250.0, 250.0], [500.0, 250.0], [750.0, 250.0]]}],
            "ft_slots": []}


def test_crossing_lane_is_resited_clear_of_cores_and_within_hop():
    t = _type()
    assert fp.core_crossings(t)
    R = S.Router(t, 360)
    log = []
    S.resite_type(t, R, 360, log)
    assert not fp.core_crossings(t)
    s = t["internal_stations"][0]
    pts = [s["from_um"], *s["regs_um"], s["to_um"]]
    assert len(s["regs_um"]) == 3
    assert max(S.man(a, b) for a, b in zip(pts, pts[1:])) <= 405


def test_snap_edge_moves_pin_out_of_core():
    bx = [(0.0, 0.0, 300.0, 300.0)]
    p = S.snap_edge([299.9, 150.0], bx)
    assert not (bx[0][0] < p[0] < bx[0][2] and bx[0][1] < p[1] < bx[0][3])
