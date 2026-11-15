"""B6 core_place pieces for the S81 leaf ft-slot rule (FABLE-LEAF-FTSLOT 11-14): --block-shift (F1), the
--take-regs eq gate for declared +1 rows, bus lane rows (F3) and the --slot-ft face-to-core slot mask."""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_place as CP  # noqa: E402
import hub_repack as HR  # noqa: E402


def test_block_shift_moves_all_clusters_by_one_vector():
    # two rule clusters near W (34.56) and S (17.28); one far cluster; one fixed cluster
    boxes = [(34.56, 100.0, 50.0, 50.0), (200.0, 17.28, 50.0, 50.0), (300.0, 300.0, 40.0, 40.0), (10.0, 10.0, 5.0, 5.0)]
    M = SimpleNamespace(m=4, W=600.0, H=500.0, bands=None, cfg=dict(face_clear=[("W", 86.4, "."), ("S", 86.4, ".")]))
    M.cbb = np.array(boxes, dtype=float)
    M.cpos = [(x, y) for x, y, _, _ in boxes]
    M.cclr = [{"W": 86.4, "S": 86.4}] * 3 + [{}]
    M.cfix = [False, False, False, True]
    n = CP.block_shift(M, lambda s: None)
    assert n == 3
    dx, dy = M.cfg["_block_shift"]
    assert dx >= 86.4 - 34.56 - 1e-6 and dy >= 86.4 - 17.28 - 1e-6
    for k in range(3):
        assert abs((M.cpos[k][0] - boxes[k][0]) - dx) < 4.33 and abs((M.cpos[k][1] - boxes[k][1]) - dy) < 4.33
    assert M.cpos[3] == (10.0, 10.0)              # fixed cluster stays
    assert M.cpos[0][0] >= 86.4 - 1e-6 and M.cpos[1][1] >= 86.4 - 1e-6


def test_eq_gate_accepts_declared_take_regs_row_only():
    t0 = dict(internal_stations=[dict(conn="bus:leafdn_i0", bits=8, regs_um=[[1.0, 1.0]], note="")],
              hard_cores=[], outline_um=[10, 10])
    t1 = copy.deepcopy(t0)
    t1["internal_stations"][0]["regs_um"] = [[1.0, 1.0], [2.0, 2.0]]
    assert CP.eq_gate(t0, t1)                    # undeclared count change: rejected
    t1["internal_stations"][0]["note"] = " | B6 take-regs (FABLE-LEAF-FTSLOT F3): bus:leafdn_i0 1 -> 2 registers"
    assert CP.eq_gate(t0, t1) == []
    t1["internal_stations"][0]["regs_um"].append([3.0, 3.0])   # +2 is not a declared +1
    assert CP.eq_gate(t0, t1)


def test_take_class_bus_rows():
    assert CP.take_class(dict(conn="bus:leafdn_i0")) == "bus:leafdn_i0"
    assert CP.take_class(dict(conn="bus:leafup_o0")) == "bus:leafup_o0"
    assert CP.take_class(dict(conn="bus:other_bus")) is None


def test_bus_take_lanes_adds_the_depth_delta():
    Q = dict(partitions={"s_3S_L3": dict(type="T"), "s_1N_L0": dict(type="U")},
             latency=dict(lanes={"dn_s_3S_L3": dict(stations=5, cycles=15, natural=15, param="LAT_DN"),
                                 "up_s_3S_L3": dict(stations=4, cycles=12, natural=12, param="LAT_UP")}))
    out = CP.bus_take_lanes(Q, "T", {"leafdn_i0": [1, 3], "leafup_o0": [1, 2]})
    assert {x["lane"]: x["cycles"] for x in out} == {"dn_s_3S_L3": 17, "up_s_3S_L3": 13}
    assert Q["latency"]["lanes"]["dn_s_3S_L3"]["stations"] == 7 and Q["latency"]["lanes"]["up_s_3S_L3"]["param"] == "LAT_UP"


def test_slot_mask_closes_face_to_core_strip():
    W, H = 400.0, 400.0
    rects = [(34.56, 100.0, 134.56, 200.0), (200.0, 200.0, 300.0, 300.0)]
    R = HR.Raster(W, H, rects)
    assert R.free(17.28, 150.0)                  # strip between W face and the near core
    n = CP.slot_mask(R, rects, W, H, 86.4)
    assert n > 0 and not R.free(17.28, 150.0)
    assert R.free(17.28, 300.0)                  # outside the core span: still free
    assert R.free(250.0, 350.0)                  # far core (> 86.4 from every face): no strip


if __name__ == "__main__":
    for f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        f()
    print("ok")
