#!/usr/bin/env python3
"""QW-SUVM9/CTLM8: kits qfd_tt_ctlm_dv_safe8 (main) / safe8b (parallel fallback) from the safe7 kit.
Structural floorplan redesign (SAFE checklist 6) for the safe7/safe7c GPL-0307 terminal FAIL (four zero-gap SRAM row
channels, abutted 3-high p192 stacks):
  safe8 : outline 777.6 x 648.0, the six 171.3 x 153.9 p192 SRAMs at x 43.2 / 259.2, y 43.2 / 237.6 / 432.0 -- every
          origin on the 43.2 lattice, N/S channels 40.5 um (no pins on those faces), W/E pin-face channel 44.7 um
          (faces 5.2 pins/um <= 6, halo 5.4); total fill (std + hard) / outline = 46.5 %.
  safe8b: outline 777.6 x 604.8 (minimum die-slot growth), y 43.2 / 217.728 / 392.256 (8.64 track lattice, N/S channels
          20.6 um >= 20); fill 49.9 %.
u_hr (h16c, 475.2 / 43.2) and the three OPROMs (y 302.4) keep their places; the N face moves with the outline (pins keep x,
the E / S pins keep their offsets); core / hr region boxes extend to y = H - 43.2.
Netlist: rtl/qwen_dv/lp8_np (candidate8: CTLM7 + FIREDQ candidate select + registered cf)."""
import json, re, shutil, sys
from pathlib import Path
W = Path(__file__).resolve().parents[4]
SRC = W / "physical/ref_tile/qfd_tt_ctlm_dv_safe7"
STD = float(sys.argv[1]) if len(sys.argv) > 1 else 11500.37
HARD = 223021.2
VAR = {"qfd_tt_ctlm_dv_safe8": dict(h=648.0, ys=[43.2, 237.6, 432.0], tag="safe8", note="Main: all macro origins on the 43.2 lattice, 40.5 um SRAM row channels."),
       "qfd_tt_ctlm_dv_safe8b": dict(h=604.8, ys=[43.2, 217.728, 392.256], tag="safe8b", note="Parallel fallback: minimum slot growth (+43.2), 20.6 um row channels on the 8.64 track lattice."),
       # r2 (safe8/safe8b GPL-0307 again with >= 20 um channels): the divergence is the TOP-LEVEL group (pin flops + the
       # timing-driven repair_design's +2455 um2 buffers, overflow stuck at 0.97 outside the core/hr regions), not the rows
       "qfd_tt_ctlm_dv_safe8t": dict(h=648.0, ys=[43.2, 237.6, 432.0], tag="safe8t", gtd=False, note="safe8 + GPL_TIMING_DRIVEN=0 (no unowned repair buffers during global placement)."),
       "qfd_tt_ctlm_dv_safe8bt": dict(h=604.8, ys=[43.2, 217.728, 392.256], tag="safe8bt", gtd=False, note="safe8b + GPL_TIMING_DRIVEN=0.")}
SRAM_ROWS = {"u_gi.u_cal.g_m[0].u_pm.u_p192": (43.2, 0), "u_gi.u_cal.g_fifo[0].u_fifo.u_p192": (259.2, 0),
             "u_gi.u_cal.g_m[1].u_pm.u_p192": (43.2, 1), "u_gi.u_cal.g_fifo[1].u_fifo.u_p192": (259.2, 1),
             "u_gi.u_cal.g_fifo[2].u_fifo.u_p192": (43.2, 2), "u_gi.u_cal.g_fifo[3].u_fifo.u_p192": (259.2, 2)}
for name, v in VAR.items():
    dst = W / f"physical/ref_tile/{name}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns("gate_layout", "gate_result.json", "views"))
    for f in dst.iterdir():
        if f.is_file() and f.suffix in (".tcl", ".sdc", ".json", ".env", ".md"):
            f.write_text(f.read_text().replace("qfd_tt_ctlm_dv_safe7", name))
    s = json.loads((dst / "spec.json").read_text())
    H = v["h"]
    s["outline"] = {"w": 777.6, "h": H, "exact": True}
    s["sources"] = [p.replace("rtl/qwen_dv/lp7_np/", "rtl/qwen_dv/lp8_np/") for p in s["sources"]]
    for m in s["macros"]:
        if m["inst"] in SRAM_ROWS:
            x, r = SRAM_ROWS[m["inst"]]
            m["at"] = [x, v["ys"][r]]
    s["landed_record"] = "results/rtl/qw_tok_1019/ctlm8/qfd_tt_ctlm_dv_np_lp_lp_record.json"
    fill = (STD + HARD) / (777.6 * H)
    s["fill_reason"] = {"pin_bound": f"{v['tag']}: mapped bounded netlist std {STD:.2f} um2 (native8) + hard {HARD} / outline {777.6*H:.1f} = {100*fill:.1f}% total fill (40-60% band); SRAM rows split by >= 20 um channels (safe7 zero-gap stacks = GPL-0307)."}
    s["slot_change_request"] = (f"QW-SUVM9/CTLM8 {v['tag']}: outline 777.6 x 561.6 -> 777.6 x {H} (+{H-561.6:.1f} um height; die GEN must re-slot; "
                                "N-face pins keep x and move with the face, E/S pins keep their offsets); safe5 pin moves kept.")
    s["structural_recut_status"] = ("CTLM8 candidate8: FIREDQ head per-source candidates (exact, 0 edges), registered cf (+1 edge priced), "
                                    "SRAM row channels >= 20 um; ck_hr own-entry still NOT applied.")
    j = s["job"]
    j["owner"] = "QW-SUVM9/CTLM8"; j["branch"] = "claude/qw-ctlm8-1020"; j["tag"] = v["tag"]
    j["purpose"] = ("QW-SUVM9/CTLM8 10-20 " + v["tag"] + ": structural redesign of the safe7 GPL-0307 FAIL: candidate8 netlist (FIREDQ head "
                    "candidates, cf pin register), SRAM rows with channels, outline from synthesis fill. " + v["note"])
    j["extra_paths"] = [p for p in j.get("extra_paths", []) if "ctlm7_cand7" not in p and "lp7_np" not in p] + \
                       ["rtl/qwen_dv/lp8_np", "results/rtl/qw_tok_1019/ctlm8", "rtl/qwen_split/mu/qfd_sys_face_mu_dhuser_p.sv"]
    s["std_area_um2"] = STD
    if v.get("gtd") is False:
        s["orfs_vars"] = dict(s.get("orfs_vars") or {}, GPL_TIMING_DRIVEN="0")
    (dst / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    t = (dst / "lp_cone_regions.tcl").read_text()
    old = "set ry0 43.2; set ry1 518.4\nset boxes [dict create 1 {{2.16 43.2 453.6 518.4} {453.6 280.8 775.44 388.8}} 2 {{453.6 43.2 775.44 280.8} {453.6 388.8 775.44 518.4}}]"
    assert old in t
    y1 = round(H - 43.2, 3)
    t = t.replace(old, f"# CTLM8 {v['tag']}: outline height {H}: region tops follow the SRAM rows (y1 = H - 43.2)\n"
                       f"set ry0 43.2; set ry1 {y1}\nset boxes [dict create 1 {{{{2.16 43.2 453.6 {y1}}} {{453.6 280.8 775.44 388.8}}}} 2 {{{{453.6 43.2 775.44 280.8}} {{453.6 388.8 775.44 {y1}}}}}]")
    (dst / "lp_cone_regions.tcl").write_text(t)
    print(name, "fill %.3f" % fill, [m["at"] for m in s["macros"] if m["inst"] in SRAM_ROWS])
