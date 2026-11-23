"""tests for adv_path_seat (ADV-PATH-SEAT): fixtures modeled on the S81 J7 (a6771d121e95) records of the 11-22 positives."""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
if not os.path.isfile(os.path.join(HERE, "cbc_rules.py")):         # work-dir copy: the lane clone's tools/die_plan
    sys.path.append("/srv/opentallas-scratch2/claude/PRECHECK-R2/repo/tools/die_plan")
import adv_path_seat as A  # noqa: E402

# dsdv_slice_lepw_mus_C__t1 (J7 = J8 geometry): ring stop iw (ri_w at lepk_i0, W) -> roe_d (ro_e at xring_o0, E), 1 cycle;
# kit 18a2688b741 @1: span 2,249.5 um, 28 stages, -649.5 ps post-place
LEPW = {
    "outline_um": [1442.88, 1226.88],
    "buses": [
        {"name": "xring_i0", "dir": "in", "width": 1104, "kind": "data", "face": "E", "window_um": [247.296, 487.26]},
        {"name": "lepk_i0", "dir": "in", "width": 1104, "kind": "data", "face": "W", "window_um": [837.312, 1077.276]},
        {"name": "xring_o0", "dir": "out", "width": 1104, "kind": "data", "face": "E", "window_um": [6.144, 246.108]},
        {"name": "lepk_o0", "dir": "out", "width": 1104, "kind": "data", "face": "W", "window_um": [596.16, 836.124]},
        {"name": "leafup_i0", "dir": "in", "width": 668, "kind": "data", "face": "N", "window_um": [128.448, 273.764]},
    ],
    "hard_cores": [{"inst": "u_c.u_cap", "origin_um": [34.56, 34.56], "outline_um": [336.96, 414.72]},
                   {"inst": "u_c.u_xf.g_cp[3].u_e", "origin_um": [1226.88, 734.4], "outline_um": [181.44, 190.08]}],
    "internal_stations": [{"conn": "bus:leafup_i0", "regs_um": [[478.172, 1136.646], [463.56, 769.346], [478.172, 402.046]]}],
}

# ot_s81sl_leaf__t15 ft0 (J7): in pin N, 4 stations down the W column (cores g_ln[*] start at x 43.2); kit @2 failed with a
# 5.2-um span / 1,885-um path that is a kit placement effect, not plan geometry -> must stay quiet
T15 = {
    "outline_um": [1442.88, 1226.88],
    "ft_slots": [{"name": "ft0", "in_face": "N", "in_window_um": [6.144, 66.012], "out_face": "S",
                  "out_window_um": [6.144, 66.012], "width": 276, "stations": 4,
                  "regs_um": [[36.0781, 1226.88], [34.56, 907.2], [34.56, 596.16], [34.56, 285.12]]}],
    "hard_cores": [{"inst": "u_lf.u_vp.g_ln[2].u_l", "origin_um": [43.2, 164.16], "outline_um": [114.48, 114.48]},
                   {"inst": "u_lf.u_vp.g_ln[5].u_l", "origin_um": [43.2, 293.76], "outline_um": [114.48, 114.48]},
                   {"inst": "u_lf.u_vp.g_ln[10].u_l", "origin_um": [51.84, 561.6], "outline_um": [114.48, 114.48]},
                   {"inst": "u_lf.u_vp.g_ln[9].u_l", "origin_um": [60.48, 838.08], "outline_um": [114.48, 114.48]},
                   {"inst": "u_lf.u_vp.g_ln[14].u_l", "origin_um": [77.76, 967.68], "outline_um": [114.48, 114.48]}],
}


def plan(**types):
    return {"partition_types": copy.deepcopy(types), "partitions": [{"name": f"p_{k}", "type": k} for k in types]}


def test_lepw_pass_through_flagged():
    out = A.findings(plan(dsdv_slice_lepw_mus_C__t1=LEPW), "x.json")
    hit = [x for x in out if "STAGE-DEPTH bus pass-through lepk_i0 -> xring_o0" in x]
    assert hit and "dsdv_slice_lepw_mus_C__t1" in hit[0] and "path 2274 um" in hit[0] and "~ 25 cells" in hit[0]
    assert not any("leafup_i0" in x for x in out)            # staged bus, not a pass-through pair
    assert out[-1].startswith("WARN ADV-PATH-SEAT summary:")


def test_lepw_staged_or_near_windows_quiet():
    t = copy.deepcopy(LEPW)                                   # a planned station row on both ring outputs
    t["internal_stations"] += [{"conn": "bus:xring_o0", "regs_um": [[721.4, 126.1], [1100.0, 126.1]]},
                               {"conn": "bus:lepk_o0", "regs_um": [[721.4, 716.1]]}]
    assert not any("STAGE-DEPTH" in x for x in A.findings(plan(dsdv_slice_lepw_mus_C__t1=t), "x.json"))
    t = copy.deepcopy(LEPW)                                   # a 300-um-wide piece: opposite windows 300-400 um apart
    t["outline_um"] = [300.0, 600.0]
    t["hard_cores"] = []
    for b, w in zip(t["buses"][:4], ([300.0, 400.0], [100.0, 200.0], [100.0, 200.0], [300.0, 400.0])):
        b["window_um"] = w
    assert not any("STAGE-DEPTH" in x for x in A.findings(plan(dsdv_slice_lepw_mus_C__t1=t), "x.json"))


def test_t15_real_geometry_quiet():
    assert A.findings(plan(ot_s81sl_leaf__t15=T15), "x.json") == []


def test_t15_seat_behind_core_flagged():
    t = copy.deepcopy(T15)                                    # a core across the whole W column between stations 1 and 2
    t["hard_cores"].append({"inst": "u_lf.u_blk", "origin_um": [0.0, 700.0], "outline_um": [400.0, 100.0]})
    out = A.findings(plan(ot_s81sl_leaf__t15=t), "x.json")
    hit = [x for x in out if "SEAT-DETOUR ft_slots[ft0] regs_um[1] (34.6,907.2) -> regs_um[2]" in x]
    assert hit and "span 311 um" in hit[0], out
    d = float(hit[0].split("macros is ")[1].split(" um")[0])
    assert 1030 < d < 1050                                    # 311 + 2 x (400 - 34.56): round the E end, never off the die


def test_kit_sited_ft_slot_split():
    t = {"outline_um": [2885.76, 1226.88], "hard_cores": [{"inst": "u_core.u_dec.u_chn", "origin_um": [864.0, 95.04],
                                                          "outline_um": [276.48, 138.24]}],
         "ft_slots": [{"name": "ft0", "in_face": "E", "in_window_um": [570.048, 681.372], "out_face": "W",
                       "out_window_um": [570.048, 681.372], "stations": 8, "width": 512}]}
    assert A.findings(plan(serdes__t16=t), "x.json") == []    # 2,886 um over 8 kit-sited stations
    t["ft_slots"][0]["stations"] = 0
    out = A.findings(plan(serdes__t16=t), "x.json")
    assert any("STAGE-DEPTH ft_slots[ft0] pin_in -> pin_out (no station: pin to pin)" in x for x in out)


def test_never_raises():
    assert A.findings({}, "x.json")[0].startswith("WARN ADV-PATH-SEAT not checked")
    bad = plan(t={"outline_um": "x", "ft_slots": [{"regs_um": [[1, None], "q"]}], "hard_cores": [{"origin_um": 3}]})
    out = A.findings(bad, "x.json")
    assert all(x.startswith("WARN ADV-PATH-SEAT") for x in out)
