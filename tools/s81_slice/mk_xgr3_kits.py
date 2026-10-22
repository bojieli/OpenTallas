#!/usr/bin/env python3
"""STW-S81c-COLLA-FRAME: s81sl_xgr3 (MAIN, ot_s81sl_xgr3m) / s81sl_xgr3_b (FB, ot_s81sl_xgr3) specs from s81sl_xgr / s81sl_xgr_b."""
import json, sys, os
R = sys.argv[1]; P = R + "/physical/ref_tile/"
W = 950.4
CFG = {
 "s81sl_xgr3":   dict(src="s81sl_xgr",   top="ot_s81sl_xgr3m", old_top="ot_s81sl_xgr2", H=777.6, K="32",
                      dx={64.8: 43.2, 125.28: 43.2, 216.0: 64.8, 276.48: 64.8, 367.2: 86.4, 475.2: 86.4, 583.2: 151.2, 643.68: 151.2},
                      bench_old="env XGR_TOP=ot_s81sl_xgr2 bash tools/s81_slice/xgr_bench.sh", bench_new="env XGR_TOP=ot_s81sl_xgr3m bash tools/s81_slice/xgr3_bench.sh",
                      wit="xgr3_main_bench.log", pfx_old="xgr2_main", pfx_new="xgr3m_main"),
 "s81sl_xgr3_b": dict(src="s81sl_xgr_b", top="ot_s81sl_xgr3", old_top="ot_s81sl_xgr", H=864.0, K="40",
                      dx={43.2: 64.8, 216.0: 86.4, 345.6: 108.0, 432.0: 129.6, 561.6: 216.0},
                      bench_old="bash tools/s81_slice/xgr_bench.sh", bench_new="bash tools/s81_slice/xgr3_bench.sh",
                      wit="xgr3_fb_bench.log", pfx_old="xgr_fb", pfx_new="xgr3_fb"),
}
for name, c in CFG.items():
    s = json.load(open(P + c["src"] + "/spec.json"))
    oldW = s["outline"]["w"]; assert s["outline"]["h"] == c["H"], s["outline"]
    s["name"] = name; s["top"] = c["top"]; s["outline"]["w"] = W
    srcs = s["sources"]; i = srcs.index("rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xgr.sv")
    srcs[i:i + 1] = ["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs6.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xgr.sv",
                     "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xgr3.sv"]
    for m in s["macros"]:
        x = m["at"][0]; assert x in c["dx"], (name, x); m["at"][0] = round(x + c["dx"][x], 3)
    # clk / rst_n pins keep their offset from the S-face centre
    for p in ("clk", "rst_n"):
        lo, hi = s["pin_ranges"][p]; d = W / 2 - oldW / 2; s["pin_ranges"][p] = [round(lo + d, 3), round(hi + d, 3)]
    s["orfs_vars"] = dict(s.get("orfs_vars") or {})
    s["orfs_vars"].update({"OT_CKKM_K": c["K"], "POST_IO_PLACEMENT_TCL": "physical/common_flow/macro_channel_block.tcl",
                           "OT_CHANNEL_BLOCK_UM": "20"})
    s["route"]["synth_keep_modules"] = s["route"]["synth_keep_modules"] + ["ot_s81sl_xs6_fetch", "ot_s81sl_xs6_dq0", "ot_s81sl_xs6_dq1"]
    pins = 11914
    s["fill_reason"] = {"pin_bound": (f"routing/perimeter-bound, not area: 11,914 face pins (W/E 2,554 each, N 3,759, S 3,047); "
        f"{W} x {c['H']} keeps every face <= 4 pins/um (N 3,759 / {W} = {3759 / W:.2f}/um; xgr 734.4 / 648 wide had N 5.1 / 5.8/um) "
        f"and leaves >= 56 um std-cell bands between every macro column; 37 macros 115.8k + std ~38k um2 -> ~{(115795 + 38000) / (W * c['H']):.0%} fill. "
        "Enlarged, never squeezed (PD-AUDIT xg ring)")}
    s["structural_change"] = (f"STW-S81c-COLLA-FRAME (10-22): successor of {c['src']} (0397b9edc; standalone native census FAIL max 43: "
        "u_c.u_s.g_pb[a].s_q0 / s_q1 one-hot q decodes, 6 drivers 42-43 loads) with PD-AUDIT MUST-DO: (1) master "
        f"{c['top']} = {c['old_top']} with ot_s81sl_xs6 (per-bank kept q-code copies + kept decode per line pair, <= 16 loads; "
        "calendar fetch compares registered as next-state compares: due5 -> fetch one AND-OR, no edge added), same ports / edges; "
        f"(2) outline {oldW} -> {W} wide (N face 3,759 pins <= 4/um), macro columns re-spaced (>= 56 um bands), abutted 0.024-um "
        "stack seams + every sub-20-um macro channel hard-blocked (macro_channel_block.tcl at POST_IO_PLACEMENT); "
        f"(3) k-means K {c['K']} (gate measures pin-flop spread <= 80 per root TT+FF).")
    j = s["job"]
    j["owner"] = "Claude:STW-S81c-COLLA-FRAME"; j["branch"] = "claude/s81-xgr3-1021"; j["tag"] = name.replace("s81sl_", "")
    j["purpose"] = (f"S81 end-slice u_xg master {c['top']} ({'MAIN: xgr2 + output relay stage' if name == 's81sl_xgr3' else 'FB: xgr'}; "
                    f"xs6 kept q decodes + registered calendar fetch compares), {W} x {c['H']}, K{c['K']}, sub-20-um channels blocked.")
    j["views_to"] = f"physical/ref_tile/{name}/views"; j["record_to"] = f"results/rtl/ref_tile/{name}"
    if "results/rtl/s81_xgr3_1022" not in j["extra_paths"]: j["extra_paths"].append("results/rtl/s81_xgr3_1022")
    for b in j["benches"]:
        b["cmd"] = b["cmd"].replace(c["bench_old"], c["bench_new"]).replace("tools/s81_slice/xs5_equiv.sh", "tools/s81_slice/xs6_equiv.sh")
        b["name"] = b["name"].replace(c["pfx_old"], c["pfx_new"]).replace("xs5_equiv", "xs6_equiv")
        b["cmd"] = b["cmd"].replace("{RUN}/" + c["pfx_old"], "{RUN}/" + c["pfx_new"]).replace("{RUN}/xs5_equiv", "{RUN}/xs6_equiv")
        for k in ("pass_regex", "fail_regex"):
            if k in b: b[k] = b[k].replace("top=" + c["old_top"] + "$", "top=" + c["top"] + "$").replace("XS5_EQUIV_BENCH", "XS6_EQUIV_BENCH")
        for k in ("pass_witness", "fail_witness"):
            if k in b and "rstopr" not in b[k]:
                f = os.path.basename(b[k]).replace("xgr2_main_bench.log", "xgr3_main_bench.log").replace("xgr_fb_bench.log", "xgr3_fb_bench.log").replace("xs5_equiv", "xs6_equiv")
                b[k] = "results/rtl/s81_xgr3_1022/bench/" + f
    os.makedirs(P + name, exist_ok=True)
    json.dump(s, open(P + name + "/spec.json", "w"), indent=4); open(P + name + "/spec.json", "a").write("\n")
    print(name, "ok", s["pin_ranges"], sorted(set(m["at"][0] for m in s["macros"])))
