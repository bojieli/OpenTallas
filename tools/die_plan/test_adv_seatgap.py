"""FP-CONVERGE-S81: adv_seatgap (SEAT-ORIENT, MACRO-GAP): clean plan + a mutant each."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_seatgap as S  # noqa: E402


def _t():
    # core u_a at (100,100)-(200,200); chain leaves its E face (pin x=200) going east, arrives at core u_b W face going east
    return {"outline_um": [1000, 1000],
            "hard_cores": [{"inst": "u_a", "origin_um": [100, 100], "outline_um": [100, 100], "orient": "R0"},
                           {"inst": "u_b", "origin_um": [600, 100], "outline_um": [100, 100], "orient": "R0"}],
            "internal_stations": [{"conn": "core:u_a.q|core:u_b.d", "launch": "core:u_a.q", "capture": "u_b.d", "bits": 8,
                                   "from_um": [200, 150], "regs_um": [[400, 150]], "to_um": [600, 150]}]}


def test_seat_orient_clean_and_mutant():
    a, tot, _ = S.seat_orient(_t())
    assert (a, tot) == (0, 2)
    m = copy.deepcopy(_t())
    m["internal_stations"][0]["regs_um"] = [[50, 150]]      # first hop goes west from the E-face pin: through the core
    a, tot, ex = S.seat_orient(m)
    assert a >= 1 and ex[0][1] == "launch"
    m2 = copy.deepcopy(_t())
    m2["internal_stations"][0]["regs_um"] = [[800, 150]]    # last hop arrives from the far side of the W-face pin
    a, tot, ex = S.seat_orient(m2)
    assert a == 1 and ex[0][1] == "capture"


def test_seat_orient_pin_off_face_is_ignored():
    m = copy.deepcopy(_t())
    m["internal_stations"][0]["from_um"] = [150, 150]       # pin inside the core, on no face
    assert S.seat_orient(m)[1] == 1


def test_macro_gap_clean_and_mutant():
    t = _t()
    t["hard_cores"][1]["origin_um"] = [205, 100]            # 5 um gap between u_a and u_b, no lane in it
    t["internal_stations"][0].update(from_um=[200, 50], regs_um=[[400, 50]], to_um=[600, 50])
    n, blk = S.macro_gap(t)
    assert n == 1 and blk == []
    m = copy.deepcopy(t)
    m["internal_stations"][0].update(from_um=[202, 90], regs_um=[[202, 150]], to_um=[202, 190])   # a 100 um run down the 5 um strip
    n, blk = S.macro_gap(m)
    assert n == 1 and blk and blk[0][4] == 8
    w = copy.deepcopy(t)
    w["hard_cores"][1]["origin_um"] = [220, 100]            # 20 um gap: not sub-9
    assert S.macro_gap(w)[0] == 0


def test_findings_lines():
    raw = {"partition_types": {"t": _t()}}
    out = S.findings_by_check["SEAT-ORIENT"](raw, "p.json")
    assert out[-1].startswith("WARN ADV-SEAT-ORIENT summary 0 types")
