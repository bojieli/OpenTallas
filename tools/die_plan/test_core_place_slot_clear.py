"""--slot-clear REGEX (R-LEAF-3 / R-LEAF-3b) in core_place: facing core pairs with a rule cluster on either side abut
(< 4.32 um) or keep >= 43.2 um; slot_clear_legalise moves one side of each base slot to the nearest legal,
timing-clean lattice spot and reports the pairs it cannot clear."""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_place as CP  # noqa: E402


def model(boxes, slot, fixed=(), W=600.0, H=400.0, tlimit=None):
    """boxes: [(x, y, w, h)] one cluster per core; tlimit: max Manhattan distance a cluster may move (timing stand-in)."""
    m = len(boxes)
    M = SimpleNamespace(m=m, W=W, H=H, bands=None)
    M.cbb = np.array([[x, y, w, h] for x, y, w, h in boxes], dtype=float)
    M.cpos = [(x, y) for x, y, _, _ in boxes]
    M.cslot = [k in slot for k in range(m)]
    M.cfix = [k in fixed for k in range(m)]
    M.CL = [[k] for k in range(m)]
    M.inst = ["u_c%d" % k for k in range(m)]
    M.inc = {k: [k] for k in range(m)}
    base = [tuple(p) for p in M.cpos]
    M.tviol = lambda K: sum(1 for k in K if tlimit is not None and abs(M.cpos[k][0] - base[k][0]) + abs(M.cpos[k][1] - base[k][1]) > tlimit + 1e-6)

    def legal(k, x, y, ignore=()):
        w, h = M.cbb[k, 2], M.cbb[k, 3]
        if x < 0 or y < 0 or x + w > W or y + h > H:
            return False
        for j in range(m):
            if j == k or j in ignore:
                continue
            X, Y = M.cpos[j]; Wj, Hj = M.cbb[j, 2], M.cbb[j, 3]
            gx = max(X - (x + w), x - (X + Wj)); gy = max(Y - (y + h), y - (Y + Hj))
            if max(gx, gy) < 4.32 - 1e-6:
                return False
            if (M.cslot[k] or M.cslot[j]) and ((gy < 0 and CP.slot_bad(gx)) or (gx < 0 and CP.slot_bad(gy))):
                return False
        return True
    M.legal = legal
    return M


def test_slot_bad_band():
    assert not CP.slot_bad(0.0) and not CP.slot_bad(4.31)
    assert CP.slot_bad(4.32) and CP.slot_bad(23.74) and CP.slot_bad(43.19)
    assert not CP.slot_bad(43.2) and not CP.slot_bad(150.0)


def test_pairs_need_a_rule_side_and_facing():
    # 0|1 face in x with a 21.6 slot; 2 is diagonal to 1 (no facing overlap) at 21.6
    M = model([(100, 100, 100, 100), (221.6, 100, 100, 100), (343.2, 221.6, 50, 50)], slot={0})
    assert [(k, j) for k, j, _ in CP.slot_pairs(M)] == [(0, 1)]
    M2 = model([(100, 100, 100, 100), (221.6, 100, 100, 100)], slot=set())
    assert CP.slot_pairs(M2) == []


def test_legalise_moves_the_rule_side_to_a_street():
    # vn (0, fixed big core) and a lane (1, rule) 23.76 apart -> lane goes to >= 43.2
    M = model([(100, 100, 200, 200), (323.76, 120, 100, 100)], slot={1}, fixed={0})
    moved, failed, left = CP.slot_clear_legalise(M, lambda s: None)
    assert moved == 1 and left == 0 and failed == []
    assert M.cpos[0] == (100, 100)
    gx = M.cpos[1][0] - 300
    assert gx >= 43.2 - 1e-6 or M.cpos[1][1] >= 300 + 43.2 - 1e-6 or M.cpos[1][1] + 100 <= 100 - 43.2 + 1e-6


def test_no_new_slot_with_third_core():
    # moving the lane east must not open a slot to a third rule core
    M = model([(100, 100, 200, 200), (323.76, 120, 100, 100), (470.0, 120, 100, 100)], slot={1, 2}, fixed={0}, W=700)
    CP.slot_clear_legalise(M, lambda s: None)
    assert CP.slot_pairs(M) == []


def test_timing_blocks_and_reports():
    # the lane may not move more than 8.64 um (timing): no clean spot -> reported, not moved
    M = model([(100, 100, 200, 200), (323.76, 120, 100, 100)], slot={1}, fixed={0}, tlimit=8.64)
    moved, failed, left = CP.slot_clear_legalise(M, lambda s: None)
    assert moved == 0 and left == 1 and failed[0]["a"] == "u_c0" and failed[0]["b"] == "u_c1"
    assert M.cpos[1] == (323.76, 120)


def one_core_model(win):
    """a 1-cluster TypeModel stand-in that runs the real TypeModel.legal (face windows WIN, no other rule active)."""
    M = SimpleNamespace(m=1, W=600.0, H=400.0, cfg={"gap": 4.32}, bands=None, FR=[], WIN=win, cslot=[False], cfix=[False],
                        cclr=[{}], cpos=[(0.0, 0.0)], FP=np.zeros((0, 2)), FPH=np.zeros(0))
    M.cbb = np.array([[0.0, 0.0, 100.0, 100.0]])
    M.cface = [{"R0": {"W": 0, "E": 0, "S": 0, "N": 0}}]
    M.cflip = ["R0"]
    M.need = lambda pins: 0.0
    return M


def test_window_clear_in_legal():
    # S-face window x 50..150 (landed: 86.4 um): a core over it must sit >= 86.4 off the S face
    M = one_core_model([("S", 50.0, 150.0, 86.4)])
    leg = lambda x, y: CP.TypeModel.legal(M, 0, x, y)  # noqa: E731
    assert not leg(60.0, 43.2) and leg(60.0, 86.4)
    # beside the window (no along overlap) any gap is fine
    assert leg(200.0, 8.64)
    M2 = one_core_model([])
    assert CP.TypeModel.legal(M2, 0, 60.0, 8.64)


def test_cli_flag_present():
    src = (Path(__file__).resolve().parent / "core_place.py").read_text()
    assert "--slot-clear" in src and "slot_clear_end" in src and "--window-clear" in src


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
    print("ok")



def test_overlap_guard_uses_the_core_track_offset():
    from types import SimpleNamespace

    cores = [
        {"inst": "west", "origin_um": [17.28, 190.08], "outline_um": [268.38, 221.4]},
        {"inst": "east", "origin_um": [285.12, 190.08], "outline_um": [268.38, 221.4],
         "track_offset_um": [0.54, 0.0]},
    ]
    model = SimpleNamespace(C=cores, core_origin=lambda i: cores[i]["origin_um"],
                            core_orient=lambda i: "R0")
    assert CP.overlaps(model) == 0
    cores[1]["track_offset_um"] = [0.27, 0.0]
    assert CP.overlaps(model) == 1
