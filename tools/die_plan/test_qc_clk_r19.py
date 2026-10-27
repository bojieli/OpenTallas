"""R19: spine-mesh perpendicular jog (qc_clk_mesh3.mesh jog_um) and the M8 drop end extension (clock_routed)."""
import pytest
import qc_clk_mesh3 as M
import clock_routed as CR

RC = {"M8": (1.0, 0.3), "M9": (1.0, 0.3)}


def test_mesh_off_strap_needs_jog():
    hs, vs = [(0.0, 0.0, 100.0)], [(0.0, 0.0, 100.0)]
    with pytest.raises(SystemExit):
        M.mesh(hs, vs, [(0.0, 0.0)], [(50.0, 25.0)], RC, (RC, 0.0))
    N = M.mesh(hs, vs, [(0.0, 0.0)], [(50.0, 25.0), (50.0, 25.0)], RC, (RC, 0.0), jog_um=30.0)
    xy = set(N["xy"])
    assert (50.0, 0.0) in xy and (50.0, 25.0) in xy          # strap attach point + the jogged tap
    jog_r = [r for a, b, r in N["R"] if {N["xy"][a], N["xy"][b]} == {(50.0, 0.0), (50.0, 25.0)}]
    assert len(jog_r) == 1 and jog_r[0] == pytest.approx(25.0)   # one jog, not duplicated for a repeated point


def test_m8_drop_end_extension():
    pts = [("M9", 10.0, 5.0), ("M8", 10.0, 5.0), ("M8", 9.757, 5.0), ("M7", 9.757, 5.0), ("M7", 9.757, 4.5)]
    L0, L1 = [], []
    CR._emit_steps(L0, pts)
    CR._emit_steps(L1, pts, m8_end_ext=0.08)
    assert "$e addPoint 9757 5000" in L0
    assert "$e addPoint 9757 5000 80" in L1
    assert sum(a != b for a, b in zip(L0, L1)) == 1             # only the M8 end before VIA78 changes
