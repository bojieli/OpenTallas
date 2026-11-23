"""ADV-DEPTH-VS-RTL: fixture = the real J8 istation_respace positive (53cab071c82f, bind FAILED 11-22 13:39 with
'LF_CS_DEPTH ot_s81sl_leaf__t21 swr: plan 2 stage(s) (deepest row), bound RTL 1'): leaf t21 = partition s_2S_L2 of
u_s_2S (ot_s81sl_slice_c1x_k8_cap5r_w_e6, J7 netlist die_j6_h8_gp1076.v: LF_VP_XR 5'b11111, HI_D/HO_D 20'h22222,
SWR_D 20'h11111) with OT_S81SL_VP_SRAMREG (SR 1).  J7 swr row: 1 reg; respace: 2 regs.  hi 3 = HI_D 2 + XR, ho 3 = HO_D 2
+ SR (both passed in the real bind).  Reduced fixture: only the hi / ho / swr rows of t21 are kept, so the
netlist's leaf-2 nibbles of VNI / Y / SW / RAR (1 in the real netlist, rows not copied) are zeroed."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_depth_vs_rtl as A  # noqa: E402

NET = ("module ot_s81_die (input wire clk);\n"
       "  ot_s81sl_slice_c1x_k8_cap5r_w_e6 #(.LF_VP_XR(5'b11111), .LF_CS_HI_D(20'h22222), .LF_CS_HI_GS(20'h22222), "
       ".LF_CS_HO_D(20'h22222), .LF_CS_HO_GS(20'h22222), .LF_CS_H_G(20'h44444), .LF_CS_VNI_D(20'h01011), "
       ".LF_CS_VNO_D(20'h00000), .LF_CS_Y_D(20'h11011), .LF_CS_U_D(20'h00000), .LF_CS_SW_D(20'h11011), "
       ".LF_CS_SWR_D(20'h11111), .LF_CS_RA_D(20'h00000), .LF_CS_RAR_D(20'h10000), .LF_CS_VE_D(20'h00000), "
       ".LF_CS_VER_D(20'h00000), .LF_CS_PVS_D(20'h00000), .LF_CS_VSP_D(20'h00000)) u_s_2S (.ck_C(ck_sl_s_2S_C), "
       ".sid(4'd4), .fault(f_s_2S));\nendmodule\n")

ROW_SWR = {"conn": "core:u_lf.u_vsw.o_f|core:u_lf.u_vs", "launch": "core:u_lf.u_vsw.o_f", "capture": "u_lf.u_vs.sw_v",
           "bits": 1, "from_um": [301.932, 302.442], "to_um": [146.922, 747.18], "regs_um": [[239.76, 540.0]]}
ROW_HI = {"conn": "core:u_lf.u_vn.u_a.hq_v|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hq_v",
          "capture": "u_lf.u_vp.g_ln[11].u_l", "bits": 1, "from_um": [909.426, 754.776], "to_um": [807.948, 1101.612],
          "regs_um": [[989.28, 920.16], [993.6, 1041.12], [807.84, 1101.6]]}
ROW_HO = {"conn": "core:u_lf.u_vn.u_a.hw_v|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hw_v",
          "capture": "u_lf.u_vp.g_ln[11].u_l", "bits": 1, "from_um": [909.426, 704.28], "to_um": [807.948, 1101.612],
          "regs_um": [[989.28, 772.293], [989.28, 920.16], [993.6, 1041.12]]}


def _tree(tmp_path):
    d = tmp_path / "physical/die_plan/s81/plan_of_record/native_bind"
    d.mkdir(parents=True)
    (tmp_path / "physical/die_plan/s81/bind/inputs").mkdir(parents=True)
    (tmp_path / "physical/die_plan/s81/bind/inputs/die_j6_h8_gp1076.v").write_text(NET)
    (d / "asbuilt_run.json").write_text(json.dumps({"netlist": ["physical/die_plan/s81/bind/inputs/die_j6_h8_gp1076.v"],
                                                    "defines": ["OT_S81SL_VP_SRAMREG"], "leaf_cs_depth_gate": True}))
    return tmp_path


def _plan(swr_regs):
    swr = copy.deepcopy(ROW_SWR)
    swr["regs_um"] = swr_regs
    t = {"module": "s81p_ot_s81sl_leaf__t21", "hard_cores": [{"inst": "u_lf.u_ve.u_m", "module": "ot_s81sl_ve_m"}],
         "verilog_defines": ["OT_S81SL_VP_SRAMREG", "OT_S81SL_VP_CFX"],
         "internal_stations": [ROW_HI, ROW_HO, swr,
                               {"conn": "bus:leafup_o0", "regs_um": [[1, 1]] * 5}]}     # bus rows are not leaf chains
    return {"partition_types": {"ot_s81sl_leaf__t21": t},
            "partitions": [{"name": "s_2S_L2", "type": "ot_s81sl_leaf__t21", "origin_um": [13685.76, 8415.36]}],
            "lanes": [{"id": "rt_W0_in_1", "fixed_cycles": 4, "ports": ["rt_W0_in_1__0"]}],
            "latency": {"lanes": {"rt_W0_in_1": {"cycles": 50, "stations": 30, "boundary": 2, "faces": 7, "fixed": 4,
                                                 "clock_landing": 14, "natural": 50, "pad": 0}}}}


def test_respace_positive_is_flagged(tmp_path):
    tree = _tree(tmp_path)
    out = A.findings(_plan([[313.148, 440.186], [146.922, 547.264]]), "plan.json", str(tree))
    hits = [x for x in out if "ot_s81sl_leaf__t21 swr: plan 2 stage(s) (deepest row) > RTL 1" in x]
    assert len(hits) == 1, out
    assert "u_s_2S LF_CS_SWR_D nibble 2" in hits[0]
    assert not any(" hi:" in x or " ho:" in x for x in out), out          # XR / SR priced: hi 3 = 2 + 1, ho 3 = 2 + 1
    assert out[-1].startswith("WARN ADV-DEPTH-VS-RTL summary: LF_CS 1 plan>RTL + 0 plan<RTL"), out


def test_j7_depth_is_clean(tmp_path):
    out = A.findings(_plan([[239.76, 540.0]]), "plan.json", str(_tree(tmp_path)))
    assert len(out) == 1 and "LF_CS 0 plan>RTL + 0 plan<RTL" in out[0] and "lanes 0/1" in out[0], out


def test_unplanned_rtl_stage_and_lane_misprice(tmp_path):
    raw = _plan([])
    raw["lanes"][0]["fixed_cycles"] = 3                                      # station added, lane not re-priced
    out = A.findings(raw, "plan.json", str(_tree(tmp_path)))
    assert any("ot_s81sl_leaf__t21 swr: plan 0 stage(s) < RTL 1" in x for x in out), out
    assert any("lane rt_W0_in_1: lanes.fixed_cycles 3 != latency.fixed 4" in x for x in out), out


def test_no_netlist_and_garbage_never_raise(tmp_path):
    out = A.findings(_plan([[1, 1]]), "plan.json", str(tmp_path))
    assert any("not checked" in x for x in out), out
    assert A.findings({"partition_types": None, "partitions": 5}, "p", None)[0].startswith("WARN ADV-DEPTH-VS-RTL not checked")
    assert A.findings({"partition_types": {}, "partitions": []}, "p", None) == []
