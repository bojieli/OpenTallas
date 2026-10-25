#!/usr/bin/env python3
"""S81/LEAFPLAN2 10-25: lane-side rule (gen_plan_v4.core_lanes_behind) on a synthetic leaf: vn halves with the lane
face W, 16 lanes in front -> 0; one lane moved behind the face -> 2 (one per vn half); a non-lane core reaching into
the lane field -> 2; the store SRAMs are exempt; the x-mirrored vn view (lane face E) flips the field.
usage (repo root): python3 -m pytest -q physical/die_plan/s81/cores/leaf/test_lane_side.py"""
import os
import sys

R = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(R, "physical/die_plan/s81"))
sys.path.insert(0, os.path.join(R, "tools/die_plan"))
os.chdir(R)
import gen_plan_v4 as G  # noqa: E402

SPEC = G.NONFRAME_HC["leaf"]
CORES = {c["inst"]: c for c in SPEC["cores"]}
SZ = {i: G._lef_size(c["lef"]) for i, c in CORES.items()}


def build(place, views=None):
    o = []
    for i, (x, y) in place.items():
        o.append(G._core_view(SPEC, CORES[i], (views or {}).get(i), origin_um=[x, y], outline_um=SZ[i], orient="R0",
                              track_offset_um=list(G.CORE_TRACK_OFFSET)))
    return o


def base(vn_x=700.0):
    p = {"u_lf.u_vn.u_a": (vn_x, 300.0), "u_lf.u_vn.u_b": (vn_x, 481.44)}
    for i in range(16):
        p["u_lf.u_vp.g_ln[%d].u_l" % i] = (vn_x - 140.0 - 130.0 * (i % 4), 100.0 + 130.0 * (i // 4))
    p["u_lf.u_vs"] = (vn_x + 400.0, 300.0)
    p["u_lf.u_vp.u_b0"] = (vn_x - 200.0, 900.0)
    return p


def test_front_ok():
    assert G.core_lanes_behind("leaf", build(base()))[0] == 0


def test_lane_behind():
    p = base()
    p["u_lf.u_vp.g_ln[0].u_l"] = (1150.0, 900.0)
    assert G.core_lanes_behind("leaf", build(p))[0] == 2


def test_core_in_field():
    p = base()
    p["u_lf.u_vs"] = (300.0, 800.0)
    n, um = G.core_lanes_behind("leaf", build(p))
    assert n == 2 and um > 0


def test_store_exempt():
    p = base()
    p["u_lf.u_vp.u_b0"] = (100.0, 900.0)
    assert G.core_lanes_behind("leaf", build(p))[0] == 0


def test_xm_view_flips_field():
    v = {"u_lf.u_vn.u_a": "xm", "u_lf.u_vn.u_b": "xm"}
    # every lane now behind (16 x 2) and vs (E of vn) inside the E-side field (x 2)
    assert G.core_lanes_behind("leaf", build(base(), v))[0] == 34


def test_other_keys_unchecked():
    assert G.core_lanes_behind("svc", build(base())) == (0, 0.0)
