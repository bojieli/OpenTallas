#!/usr/bin/env python3
"""S81-LEAF-PLAN B4L4 (COORD 11-14): core_place --ft-resite / --link-reg helpers."""
import copy
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_place as CP  # noqa: E402
import hub_repack as HR  # noqa: E402
import kit_istations as KI  # noqa: E402


def _type():
    return dict(hard_cores=[dict(inst="u_lf.u_vs", module="m", origin_um=[0, 0])],
                internal_stations=[dict(conn="core:u_lf.u_vs.sw_d|core:u_lf.u_vsw.i_d", regs_um=[[10.0, 10.0]], bits=4,
                                        from_um=[1, 1], to_um=[2, 2])],
                ft_slots=[dict(name="ft0", in_face="W", out_face="E", width=2, in_window_um=[100, 110],
                               out_window_um=[100, 110], regs_um=[[200.88, 103.68], [401.76, 103.68]],
                               bit_sites_um=[[[200.88, 103.68], [200.88, 104.22]], [[401.76, 103.68], [401.76, 104.22]]])],
                outline_um=[600, 300])


def test_eq_gate_link_reg_rows():
    t0 = _type()
    t1 = copy.deepcopy(t0)
    t1["internal_stations"].append(dict(conn="core:u_lf.u_vsw.o_d|core:u_lf.u_vs", regs_um=[[5, 5]], bits=32,
                                        note="B4L4 link-reg (COORD 11-14): +1 register on class swr"))
    assert CP.eq_gate(t0, t1) == []
    t1["internal_stations"][-1]["note"] = "something else"
    assert CP.eq_gate(t0, t1) != []


def test_eq_gate_bus_reg_rows():
    t0 = _type()
    t1 = copy.deepcopy(t0)
    t1["internal_stations"].append(dict(conn="bus:leafup_o0", launch="face bus leafup_o0", capture="u_lf.u_vq.xf",
                                        regs_um=[[5, 5]], bits=276, note="B6 bus-reg (COORD 11-14): sites ..."))
    assert CP.eq_gate(t0, t1) == []


def test_eq_gate_ft_coords_only():
    t0 = _type()
    t1 = copy.deepcopy(t0)
    t1["ft_slots"][0]["regs_um"][0] = [250.56, 120.96]
    t1["ft_slots"][0]["note"] = "B4L4 ft-resite: 1 regs re-sited, count kept"
    assert CP.eq_gate(t0, t1) == []
    t1["ft_slots"][0]["regs_um"].append([300.0, 100.0])
    assert "ft_slots" in CP.eq_gate(t0, t1)


def test_link_class():
    assert CP.link_class(KI, "u_lf.u_vsw", "o_d", "u_lf.u_vs", "sw_d") == "swr"
    assert CP.link_class(KI, "u_lf.u_vs", "ra_fi", "u_lf.u_rxsb", "o_f") == "rar"
    assert CP.link_class(KI, "u_lf.u_rxsb", "o_r", "u_lf.u_vs", None) == "rar"


def test_ft_resite_moves_covered_reg_keeps_count():
    t = _type()
    W, H = 600.0, 300.0
    R = HR.Raster(W, H, [(180.0, 80.0, 230.0, 130.0)])     # a moved core now covers ft0 reg 0 + its bit group
    M = types.SimpleNamespace(W=W, H=H, owner=lambda p, tol=0.6: None, moved_core=lambda i: True)
    rep = {}
    CP.ft_resite(M, t, R, dict(reach=360.0), rep)
    f = t["ft_slots"][0]
    assert rep["ft_failed"] == 0 and rep["ft_regs_moved"] == 1
    assert len(f["regs_um"]) == 2 and len(f["bit_sites_um"]) == 2
    assert R.free(*f["regs_um"][0]) and f["regs_um"][1] == [401.76, 103.68]
    assert all(R.free(*p) for p in f["bit_sites_um"][0])
    d = [f["bit_sites_um"][0][1][k] - f["bit_sites_um"][0][0][k] for k in (0, 1)]
    assert abs(d[0]) < 1e-6 and abs(d[1] - 0.54) < 1e-6          # the group moves rigidly with its register


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
    print("ok")


def test_snap_station_moves_regs_off_a_core():
    # B6 A2: a register under a core snaps to the nearest free lattice point; hops stay within reach
    R = HR.Raster(200.0, 200.0, [(80.0, 80.0, 120.0, 120.0)])
    out = CP.snap_station(R, (10.0, 100.0), (190.0, 100.0), [[99.36, 99.36]], 405.0)
    assert out is not None and len(out) == 1 and R.free(*out[0])
    assert CP.snap_station(R, (10.0, 100.0), (190.0, 100.0), [[99.36, 99.36]], 50.0) is None


def test_detour_fix_shortens_a_kept_station():
    R = HR.Raster(400.0, 400.0, [])
    st = [dict(from_um=[100.0, 100.0], to_um=[200.0, 100.0], regs_um=[[100.0, 300.0]], bits=8, conn="x")]
    rep = {}
    CP.detour_fix(R, st, dict(reach=405.0), rep)
    assert rep["detour_fixed"] == 1 and len(st[0]["regs_um"]) == 1
    assert abs(st[0]["regs_um"][0][1] - 300.0) > 50
