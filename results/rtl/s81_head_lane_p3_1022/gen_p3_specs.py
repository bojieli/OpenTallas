#!/usr/bin/env python3
"""STW-S81c-HEAD-LANE 10-22 (RELEASE FREEZE: ot_s81hd_lane ports / widths / timing contract unchanged, no RTL change):
s81hd_lane_p3m (MAIN) / s81hd_lane_p3f (FALLBACK) = ot_s81hd_lane as a CLUSTER: hard child u_ln = the CLOSED view
dscoll_lane_w_s8ng (dsfd_coll_lane_w_safe8_ntf, default CORE_CRED 8 = the instance's parameters; closure-loop
dscoll_lane_w_s8ng-s8ng-8151c3923 TT +9.95 / FF +6.81 DRC 0, its own k-means tree, routed boundary spread TT 73.5 / FF
67.6) + the static adapter as parent soft logic on a balanced spine whose target is the child's boundary pin-register
insertion (child_clock_ref boundary).  The 19.7k lane flops leave the parent tree (old flat m/f: one 24.1k-sink tree,
boundary spread TT 81.5 / FF 83.0 / f TT 112.9).  MAIN: core face E (as m/f); FB: core face N (H10 core-link face)."""
import json, copy
from pathlib import Path
base = json.load(open("physical/ref_tile/s81hd_lane_m/spec.json"))
CH = "physical/ref_tile/dscoll_lane_w_s8ng/views/dsfd_coll_lane_w_safe8_ntf"
def spec(name, w, h, faces, ranges, main):
    s = copy.deepcopy(base)
    s["name"] = name
    s["kind"] = "cluster"
    s["sources"] = ["rtl/lib/ot_rst_relay_tree3.sv", "rtl/dsrom_sys/s81_head/ot_s81hd_util.sv", "rtl/dsrom_sys/s81_head/ot_s81hd_lane.sv"]
    s["outline"] = {"w": w, "h": h, "exact": True}
    s["macros"] = []
    s["children"] = [{"view": CH, "count": 1, "inst": "*u_ln", "at": [43.2, 43.2], "orient": "R0"}]
    s["child_clock_ref"] = "boundary"
    s["child_clock_ref_reason"] = ("the parent adapter talks to the child's boundary pin registers (lo_* landing, li_* sender, W-face rx/tx "
                                   "flops): target = the child's routed boundary insertion (insertion.json TT mean 698.4), not its deepest leaf")
    s.pop("clock", None)
    for k in ("pre_cts_extra", "orfs_vars", "boundary_tcl", "sdc_extra", "defines", "std_area_um2"):
        s.pop(k, None)
    s["std_area_um2"] = 2600.0
    s["route"]["synth_keep_modules"] = ["ot_s81hd_kf", "ot_s81hd_lane_txs"]
    s["pins"] = faces
    s["pin_ranges"] = ranges
    s["pin_regs"] = {"enable": False, "reason": "Source-registered, unchanged RTL (release freeze): tx_d -> txd_p, tx_v -> 2 kept ot_s81hd_kf pin flops, rx_v / rx_d / flt leave flops (rv_q / rd_q / flt_q); rx / tx / chb are wires to the CLOSED child's own pin registers (lr landing, gearbox beat, endpoint chb flop). A recipe pin stage would change the frozen latency contract."}
    s["reset_landing"] = {"enable": True, "stages": 2, "clock": "ck", "reason": "rst_n lands in 2 ck flops at the core face, then ot_rst_relay_tree3 (35 slice leaves + lane + rx + misc, every leaf <= ~32 reset pins); the child lands its own rs (tree3 inside the closed view)"}
    s["slot_change_request"] = {"reason": ("H10 reserve ln_* is 518.4 x 1123.2 R0; the closed lane child is 725.76 x 583.2 (no R90 for SRAM views), so "
        f"the head die re-slots the 13 lanes to {w} x {h} (area {w*h/1e6:.3f} mm2 vs 0.582 reserve). Ports / widths / protocol / cycles unchanged (freeze). "
        "Faces: SerDes rx/tx on W (MY for the E-SerDes lanes); core tx_d/rx_d/v/flt/ck/rst_n/chb on " + ("E (as m/f)." if main else "N (the H10 core_i/core_o face)."))}
    s["fill_reason"] = {"pin_bound": "child-bound: the CLOSED 725.76 x 583.2 lane view + a 43.2-um ring + the adapter band; parent std ~2.6k um2 (adapter 3-flit buffer in 35 kept slices + pin flops) in the band; never shrink."}
    s["structural_change"] = (
        "STW-S81c-HEAD-LANE 10-22 (successor of flat s81hd_lane_m/f: clock_rule FAIL, one 24.1k-sink root over 812 um, boundary spread TT 81.5/FF 83.0 (m), "
        "TT 112.9 (f)): HIERARCHICAL -- the lane body is the CLOSED hard child dscoll_lane_w_s8ng (own tree, routed boundary spread TT 73.5/FF 67.6; "
        "closure-loop 8151c3923 TT +9.95/FF +6.81 DRC 0), the adapter is parent soft logic on a balanced spine targeted at the child's boundary "
        "insertion. RTL, ports, widths, cycles unchanged (RELEASE FREEZE 10-22). Two-root flat variant (+ck_l port) parked NEXT-RELEASE "
        "(branch claude/s81-head-lane-p2-1021). " + ("MAIN: core face E, adapter band 129.6 um E." if main else "FALLBACK: core face N (H10 link face), adapter L-band (E 129.6 + N 172.8)."))
    j = s["job"]
    j["owner"] = "Claude:STW-S81c-HEAD-LANE"
    j["branch"] = "claude/s81-head-lane-p3-1022"
    j["tag"] = name
    j["purpose"] = "S81.HEAD.LANE: head-die lane block as cluster (CLOSED s8ng lane child + static adapter), frozen interface, to closure (TT setup / FF hold / DRC 0). " + ("MAIN" if main else "FALLBACK")
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    j["extra_paths"] = [p for p in j["extra_paths"] if "clock_split_km" not in p] + ["physical/ref_tile/dscoll_lane_w_s8ng/views", "results/rtl/s81_head_lane_p3_1022"]
    d = Path(f"physical/ref_tile/{name}"); d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print(name, w, h)
o = 43.2
mr = {"rx": [o + 2.16, o + 288.36], "tx": [o + 290.52, o + 576.72],
      "tx_d": [o + 2.16, o + 274.32], "tx_v": [o + 276.48, o + 277.56], "chb": [o + 280.8, o + 282.96], "ck": [o + 298.08, o + 300.24],
      "rst_n": [o + 302.4, o + 304.56], "rx_v": [o + 306.72, o + 307.8], "flt": [o + 310.0, o + 315.36], "rx_d": [o + 317.52, o + 581.04]}
spec("s81hd_lane_p3m", 898.56, 669.6, {"W": ["rx", "tx"], "E": ["tx_v", "tx_d", "rx_v", "rx_d", "flt", "ck", "rst_n", "chb"]},
     {k: [round(a, 2), round(b, 2)] for k, (a, b) in mr.items()}, True)
fr = {"rx": [o + 2.16, o + 288.36], "tx": [o + 290.52, o + 576.72],
      "tx_d": [302.4, 576.0], "tx_v": [578.16, 579.24], "chb": [581.4, 583.56], "ck": [585.72, 587.88], "rst_n": [590.04, 592.2],
      "rx_v": [594.36, 595.44], "flt": [597.6, 603.0], "rx_d": [605.16, 878.4]}
spec("s81hd_lane_p3f", 898.56, 799.2, {"W": ["rx", "tx"], "N": ["tx_d", "tx_v", "chb", "ck", "rst_n", "rx_v", "flt", "rx_d"]}, fr, False)
