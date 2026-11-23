"""ADV-LAND-CAP on fixtures modelled on the two real positives (S81 J8 v9 dsdv_slice_c1x_C__t9, QC V3 st_a x_st_b_i)."""
import copy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_land_cap as A  # noqa: E402


def _band(rect, width, rw):
    return {"rect_um": rect, "width": width, "ring_width": rw, "ring_place": "ff", "instance": "u_cland_x",
            "live_data_storage_flops": 5 * (width + 1), "padded_data_storage_flops": 5 * rw}


def s81_t9():
    """J8 v9 t9: c1x core moves put u_c.u_xr over leafup_i3 and u_c.u_cap over xtier_i0 / xring_i1 (kit: OT_CLAND BAND FAIL x3)"""
    t = {"outline_um": [1442.88, 1226.88],
         "hard_cores": [{"inst": "u_c.u_xr", "origin_um": [432.0, 69.12], "outline_um": [207.36, 164.16]},
                        {"inst": "u_c.u_cap", "origin_um": [69.12, 69.12], "outline_um": [336.96, 414.72]}],
         "clock": {"landing_contract": {
             "bands": {"leafup_i3": _band([611.28, 17.28, 650.16, 162.596], 668, 704),
                       "leafup_i4": _band([824.45, 17.28, 969.76, 56.16], 668, 704),
                       "xtier_i0": _band([378.0, 30.24, 390.96, 213.84], 276, 320),
                       "ft1_i": _band([17.28, 17.28, 237.6, 28.08], 276, 320),
                       "xring_i1": _band([17.28, 455.76, 257.24, 494.64], 1104, 1152)},
             "pins": [{"name": "fclk_in_leafup_i3", "xy_um": [564.832, 2.656]},
                      {"name": "fclk_in_leafup_i4", "xy_um": [897.056, 2.656]},
                      {"name": "fclk_in_xtier_i0", "xy_um": [380.0, 2.656]},
                      {"name": "fclk_in_ft1_i", "xy_um": [36.064, 2.656]},
                      {"name": "fclk_in_xring_i1", "xy_um": [2.656, 470.0]}]}}}
    return {"partition_types": {"dsdv_slice_c1x_C__t9": t}, "partitions": [{"name": "s_6N_C", "type": "dsdv_slice_c1x_C__t9"}]}


def qc_st_a(btb_y=708.48):
    """V3 slw_st_a_v2__clf4365a62: btab g_btb[3].u_m (halo 4.32) under the E-face x_st_b_i band (kit: band overlaps hard
    placement blockage {561.384 708.492 563.436 749.556})"""
    t = {"outline_um": [622.08, 1339.2],
         "hard_cores": [{"inst": "u_bound.u_u_btab.u_bt.u_core.g_btb[3].u_m", "origin_um": [466.56, btb_y],
                         "outline_um": [94.82, 41.06], "halo_um": 4.32}],
         "clock": {"landing_contract": {"bands": {"x_st_b_i": _band([520.56, 713.008, 604.8, 721.648], 8, 64)},
                                        "pins": [{"name": "fclk_in_x_st_b_i", "xy_um": [622.08, 716.7]}]}}}
    return {"partition_types": {"slw_st_a_v2__clf4365a62": t}, "partitions": [{"name": "st_a0", "type": "slw_st_a_v2__clf4365a62"}]}


def _fills(raw):
    return {(tn, nm): (f, i) for tn, nm, f, i in A.band_fills(raw)}


def test_s81_t9_positive():
    f = _fills(s81_t9())
    t = "dsdv_slice_c1x_C__t9"
    for nm in ("leafup_i3", "xtier_i0", "xring_i1"):
        assert f[(t, nm)][0] >= A.FILL_WARN, (nm, f[(t, nm)][0])
    assert f[(t, "leafup_i3")][1]["flops"] == 3915            # kit OT_CLAND strip density: 3913 flops
    assert f[(t, "leafup_i3")][1]["form"] == "S strip 32 cols rows 3"   # kit: 32 columns, rows 3
    assert f[(t, "xtier_i0")][1]["form"] == "S strip 10 cols rows 3"    # kit: 10 columns, rows 3
    for nm in ("leafup_i4", "ft1_i"):                         # placed in the same kit
        assert f[(t, nm)][0] < 0.75, (nm, f[(t, nm)][0])
    out = A.findings(s81_t9(), "plan.json")
    assert any("dsdv_slice_c1x_C__t9: band leafup_i3 fill 1.37" in ln for ln in out), out
    assert out[-1].startswith("WARN ADV-LAND-CAP 3 band(s) in 1 type(s)")


def test_s81_t9_fixed_cores_clear():
    raw = s81_t9()
    t = raw["partition_types"]["dsdv_slice_c1x_C__t9"]
    t["hard_cores"][0]["origin_um"] = [400.0, 200.0]      # u_xr clear of leafup_i3 (+ row cut)
    t["hard_cores"][1]["origin_um"] = [69.12, 500.0]      # u_cap clear of xtier_i0 / xring_i1
    out = A.findings(raw, "plan.json")
    assert not [ln for ln in out[:-1] if "fill" in ln], out
    assert "0 band(s) in 0 type(s)" in out[-1]


def test_qc_st_a_halo_blocked():
    f = _fills(qc_st_a())
    fill, info = f[("slw_st_a_v2__clf4365a62", "x_st_b_i")]
    assert fill == math.inf and info["blocked"][0][0].endswith("g_btb[3].u_m")
    out = A.findings(qc_st_a(), "plan.json")
    assert any("BLOCKED" in ln and "x_st_b_i" in ln for ln in out), out


def test_qc_v4_band_move_still_blocked_by_halo():
    # V4 l0b / v5c: g_btb[3] moved to y 725.76; its 4.32-um halo starts at 721.44 < band top 721.648 (0.21 um overlap)
    fill, info = _fills(qc_st_a(725.76))[("slw_st_a_v2__clf4365a62", "x_st_b_i")]
    assert fill == math.inf and info["blocked"]


def test_qc_twin_clear():
    # slw_st_a_v2__cl9f076a5c twin (placed): no btab under the band; and a move by >= halo clears it
    raw = qc_st_a(800.0)
    fill, info = _fills(raw)[("slw_st_a_v2__clf4365a62", "x_st_b_i")]
    assert fill < 0.3 and not info["blocked"]
    fill2, _ = _fills(qc_st_a(726.03))[("slw_st_a_v2__clf4365a62", "x_st_b_i")]
    assert fill2 < A.FILL_WARN


def test_hard_ring_child_band_skipped_and_never_raises():
    raw = copy.deepcopy(qc_st_a())
    t = raw["partition_types"]["slw_st_a_v2__clf4365a62"]
    t["hard_cores"].append({"inst": "cl_x_st_b_i", "origin_um": [520.56, 713.0], "outline_um": [84.24, 8.64]})
    assert A.band_fills(raw) == []
    assert A.findings({"partition_types": {"x": {"clock": 3}}}, "p")[0].startswith("WARN ADV-LAND-CAP not checked")
    assert A.findings(None, "p")[0].startswith("WARN ADV-LAND-CAP not checked")
