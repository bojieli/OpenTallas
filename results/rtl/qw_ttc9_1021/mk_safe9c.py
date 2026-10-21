#!/usr/bin/env python3
"""QW-TTC9 10-21: CALR successor kits qfd_tt_ctlm_dv_safe9c / safe9co / safe9cb (Q.STA.TTC.4) from the TTC8 safe8u/8bu kits.
safe8u / safe8bu gates FAILED (GRT overflow 0, DPL fixed) on two structural items, fixed here:
 (1) cross_clock: every failing endpoint is a landing ring->read path (u_lpl_<n>_w -> u_lpl_<n>_r) timed single-cycle,
     because the bound netlist renamed the landing cells u_<idx> and the kit fell back to no_data_multicycle.
     Fix: netlist rtl/qwen_dv/lp9d_npl = lp9d_np with the landing instances renamed back (landing_names.py, exact
     construct replay), record copy without no_data_multicycle -> the lp.py L5 contract (-setup E=2 / -hold D-1=3,
     sample age 1.25..2.75 T) binds again.  Logic, connections and order unchanged.
 (2) clock_rule: per-root pin-flop spread (ck_core 217 TT, ck_hr 263 TT).  Per-register dump of the safe8u CTS odb:
     the late flops are the pin-band registers in the 43 um strip UNDER the macro rows (ck_hr S strip under u_hr x
     605: 640-752 ps vs 500-530 everywhere else; ck_core S strip under the SRAM rows: 935-1043 ps, NE 810-850).  Same
     signature as qkd_d2d_static 10-15 (max-cap sink clustering hangs pin-band leaves on long return wires) and s81
     gather 10-14 (obstruction-aware H-tree detours around macro stacks).  Fix: route.cts_sink sink_clustering false
     (safe9c) / + -no_obstruction_aware (safe9co, safe9cb).
CALR content (QW-CALR / QW-TLPROD): lp9d_np (PRIVATE_CALR=1, F16WTN=1, TABLE_REL producer), 2 ROM266 calendar ROMs on
ck_core at (475.2,388.8) / (475.2,475.2), closed wtn child (wtn1-9fa6fd27d) at (648.0,388.8)."""
import json, shutil
from pathlib import Path
W = Path(__file__).resolve().parents[3]
HARD0 = 223021.2
ROM266 = (121.824, 62.91)
WTN = (86.4, 77.76)
STD = 12270.0   # estimate: native8 11,970.92 x 68,742 / 67,065 cells (lp9d_np construct); the gate reports the synthesis value
VAR = {"qfd_tt_ctlm_dv_safe9c": dict(src="qfd_tt_ctlm_dv_safe8u", h=648.0, cts={"sink_clustering": False},
                                     note="safe8u outline; CTS unclustered H-tree (pin-band strip leaves)."),
       "qfd_tt_ctlm_dv_safe9co": dict(src="qfd_tt_ctlm_dv_safe8u", h=648.0, cts={"sink_clustering": False, "extra": "-no_obstruction_aware"},
                                      note="safe8u outline; CTS unclustered + no obstruction-aware detour (parallel)."),
       "qfd_tt_ctlm_dv_safe9cb": dict(src="qfd_tt_ctlm_dv_safe8bu", h=604.8, cts={"sink_clustering": False, "extra": "-no_obstruction_aware"},
                                      note="safe8bu outline (604.8); CTS unclustered + no obstruction-aware (fallback).")}
REC = "results/rtl/qw_ttc9_1021/qfd_tt_ctlm_dv_np_lp_lp_record.json"
rec = json.loads((W / "results/rtl/qw_tok_1019/ctlm8/qfd_tt_ctlm_dv_np_lp_lp_record.json").read_text())
rec["landing_implementation"].pop("no_data_multicycle", None)
rec["ttc9_derived"] = {"from": "results/rtl/qw_tok_1019/ctlm8/qfd_tt_ctlm_dv_np_lp_lp_record.json",
                       "change": "no_data_multicycle removed: lp9d_npl carries the u_lpl_<n>_w / _r landing instance names again "
                                 "(results/rtl/qw_ttc9_1021/landing_names.py), so the L5 multicycle binds (30 of 31 landings have "
                                 "cells; landing 3 dh_user is unread in u_gi and has none). Regions, D/E/K, landings, reset runs unchanged; "
                                 "CALR (lp9d) adds no landing (QW-CALR README: unchanged landed record)."}
(W / REC).write_text(json.dumps(rec, indent=1) + "\n")
for name, v in VAR.items():
    src = W / f"physical/ref_tile/{v['src']}"
    dst = W / f"physical/ref_tile/{name}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("gate_layout", "gate_result.json", "views"))
    for f in dst.iterdir():
        if f.is_file() and f.suffix in (".tcl", ".sdc", ".json", ".env", ".md"):
            f.write_text(f.read_text().replace(v["src"], name))
    s = json.loads((dst / "spec.json").read_text())
    assert s["outline"]["h"] == v["h"]
    s["sources"] = [p.replace("rtl/qwen_dv/lp8_np/", "rtl/qwen_dv/lp9d_npl/") for p in s["sources"]]
    s["sources"].append("physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v")
    s["macros"] += [{"view": "physical/asap7_memory_macros/ot_rom_4096x266_m8", "count": 1, "inst": "u_gi.u_cal.g_calrom.u_rom.m0",
                     "at": [475.2, 388.8], "orient": "R0", "at_exact": True},
                    {"view": "physical/asap7_memory_macros/ot_rom_4096x266_m8", "count": 1, "inst": "u_gi.u_cal.g_calrom.u_rom.m1",
                     "at": [475.2, 475.2], "orient": "R0", "at_exact": True}]
    s["children"].append({"view": "physical/ref_tile/qfd_tt_ctlm_dv_wtn/views/qfd_tt_ctlm_dv_wtn", "count": 1,
                          "inst": "u_gi.g_wtn.u_wtn", "at": [648.0, 388.8], "orient": "R0"})
    s["soft_root_macro_masters"] = sorted(set(s["soft_root_macro_masters"]) | {"ot_rom_4096x266_m8"})
    for m in ("m0", "m1"):
        s["soft_root_macro_bindings"][f"u_gi.u_cal.g_calrom.u_rom.{m}"] = {"master": "ot_rom_4096x266_m8", "clock_pin": "clk", "root": "ck_core"}
    s["raw_memory_note"] = s["raw_memory_note"] + " CALR (QW-TTC9): + two 4096x266 calendar ROMs u_gi.u_cal.g_calrom.u_rom.m0/m1, exact named ck_core sinks (die ROM_BIND: images/calr10 calendar_m0/m1)."
    s["landed_record"] = REC
    s["route"]["cts_sink"] = v["cts"]
    hard = HARD0 + 2 * ROM266[0] * ROM266[1] + WTN[0] * WTN[1]
    fill = (STD + hard) / (777.6 * v["h"])
    s["fill_reason"] = {"pin_bound": f"{name}: bounded netlist std ~{STD:.0f} um2 (estimate) + hard {hard:.1f} (+2 ROM266 + wtn) / outline "
                                     f"{777.6 * v['h']:.1f} = {100 * fill:.1f}% total fill (40-60% band)."}
    s["std_area_um2"] = STD
    s["structural_recut_status"] = ("CTLM9d (CALR=1, F16WTN=1, TABLE_REL) on the TTC8 floorplan; landing names restored (L5 binds); "
                                    "CTS pin-band strip fix via route.cts_sink; ck_hr own-entry still NOT applied (next if spread stays > 80).")
    s["slot_change_request"] = s["slot_change_request"] + " QW-TTC9: CALR adds table_req / f16_auth / f16_obs only (already on the faces); no pin move."
    j = s["job"]
    j["owner"] = "QW-TTC9"; j["branch"] = "claude/qw-ttc9-1021"; j["tag"] = name.rsplit("_", 1)[1]
    j["purpose"] = ("QW-TTC9 10-21 " + j["tag"] + ": CALR successor (lp9d: CALR=1, F16WTN=1, TABLE_REL) + safe8u/8bu FAIL fixes: landing names "
                    "restored so the L5 ring->read multicycles bind (cross_clock), unclustered CTS for the pin-band strips under the "
                    "macro rows (clock_rule). " + v["note"])
    j["extra_paths"] = [p for p in j["extra_paths"] if "lp8_np" not in p] + \
        ["rtl/qwen_dv/lp9d_npl", "rtl/qwen_dv/lp9d_np", "results/rtl/qw_ttc9_1021", "results/rtl/qw_tlprod_1020",
         "results/rtl/qw_calr_1020/ctlm9c", "physical/ref_tile/qfd_tt_ctlm_dv_wtn"]
    (dst / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print(name, "fill %.3f" % fill)
