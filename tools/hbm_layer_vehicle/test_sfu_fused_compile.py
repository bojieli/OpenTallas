#!/usr/bin/env python3
"""tests for sfu_fused_compile.py (HC_POST -> col_sfu_SW grid programme): row ABI, pass bases, hazards, golden mirror."""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "hbm_static"))

import sfu_fused_compile as C  # noqa: E402
from sfu_control_image import unpack  # noqa: E402

FIX = HERE.parents[1] / "results/rtl/hbm_ds_layer_tput_1018/fixtures/L02"


def test_programme():
    segs = C.hc_post_passes(D=5120, quadrant=0, A=82432, B=20480, C=41028, O=0, one=131071)
    p = C.compile_segments(segs)
    assert p["cycles"] == 1414 <= C.ROWS and p["emit_rows"] == 16 * 80
    w = [unpack(x) for x in p["words"]]
    assert w[0]["ld"] == 1 and sum(x["ld"] for x in w) == 1
    e = [x for x in w if x["emit"]]
    assert len(e) == 1280 and all(x["cp_m1"] == C.M1_AB and x["ca_ad"] == C.AD_Q and x["cm_qm"] == C.QM_POS for x in w)
    vb = [[(x["vb"] >> (24 * i)) & 0xFFFFFF for i in range(5)] for x in e]
    assert vb[0] == [20480, 41032, 25600, 41036, 0]                     # P1 k0: r0, c00, r1, c10, O_0
    assert vb[80] == [20480, 41033, 25600, 41037, 5120]                 # P1 k1
    assert vb[320] == [30720, 41040, 0, 131071, 0]                      # P2 k0: r2, c20, O_0, one
    assert vb[960] == [82432, 41028, 0, 131071, 0]                      # P4 k0: y, post0, O_0, one
    assert vb[1] == [20496, 41032, 25616, 41036, 16]                    # strides (1, 0, 1, 0, 1)
    assert all(not x["co_rnd"] for x in w[:p["rnd_from"]]) and all(x["co_rnd"] for x in w[p["rnd_from"]:])
    assert p["rnd_from"] - max(i for i, x in enumerate(w) if x["emit"] and i < p["rnd_from"]) > C.HORIZON


def test_hazard_refused():
    segs = C.hc_post_passes(D=5120, quadrant=0, A=82432, B=20480, C=41028, O=0, one=131071)
    try:
        C.compile_segments(segs[:4] + segs[4:5])        # P2 k0 right after P1 k3: 0 rows apart from P1 k0 + 240 ok
    except ValueError:
        raise AssertionError("legal order refused")
    tight = [segs[0], segs[4]]                          # P2 k0 straight after P1 k0: RAW inside the drain
    try:
        C.compile_segments(tight)
    except ValueError as e:
        assert "RAW" in str(e)
    else:
        raise AssertionError("RAW hazard not refused")


def test_golden_mirror():
    z = np.load(FIX / "operands.npz")
    g = C.golden_hc_post_slice(z["r0.k49.A"], z["r0.k49.B"], z["r0.k49.C"], 0)
    assert np.array_equal(g, z["r0.k49.O"].reshape(4, 5120)[:, :1280])


if __name__ == "__main__":
    for t in (test_programme, test_hazard_refused, test_golden_mirror):
        t()
    print("PASS")
