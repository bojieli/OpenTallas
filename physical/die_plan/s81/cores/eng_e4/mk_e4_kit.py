#!/usr/bin/env python3
"""PATH-S81/E4 (2026-10-25): build the dsdv_eng_rr_e E4 kit from the E3 kit recipe (GEOM-REVIEW 09:23: one successor
with all four structural fixes).  Interface unchanged: outline 410.4 x 466.56, pins.json / io.tcl / macro sites byte
identical to E3 (= e2 kit 812c3bee41bf6e02).  Changes against E3:
  RTL   current tree (this branch = main + E3 eng + ENG2 OHSEL + ENG3 BF_PREDEC) and VERILOG_DEFINES
        + OT_S81ENG_XQ_OHSEL + OT_S81ENG_BF_PREDEC (fck->vo_b one-hot pre-decode; bfraw decode split, 0 cycles).
  F6    ROM capture anchors: physical/common_flow/macro_pin_flops.tcl with OT_MPF_ENMUX=1 (walks the CPRE DFFE ->
        DFF + enable-feedback gates), so each bank's bank_words sit at that ROM's rd pins.
  clock MSCTS structured clock: PRE_CTS core_density_taps.tcl (port ck -> CTS trunk -> density taps <= OT_DTAP_TARGET
        sinks within OT_DTAP_DMAX_UM -> local trees; ROM/SRAM clock pin on its interface-register tap), POST_CTS
        core_tap_align.tcl (tap means within 8 ps) -> cts_post.tcl (tap_balance report + setup-only repair).
  reset rst_n pin registers (reset3n32 root) anchored at the rst_n pin (rst_pin_regs.tcl); relay unchanged (3 edges,
        32 registered leaves).
  IO    FLOW core_flow defaults: per-corner vclk OT_VCLK_TT 250 / OT_VCLK_FF 202.5 (FF-only GRT hold repair), RCX RC.
    python3 mk_e4_kit.py E3_KIT E4_KIT REPO
"""
import json
import re
import shutil
import sys
from pathlib import Path

e3, e4, repo = (Path(x).resolve() for x in sys.argv[1:4])
HERE = Path(__file__).resolve().parent
TOOL = repo / "tools/die_plan"
CF = repo / "physical/common_flow"
HB = repo / "physical/die_plan/hbm_arch_cores"
sys.path.insert(0, str(TOOL))
import core_flow  # noqa: E402

if e4.exists():
    raise SystemExit(f"{e4} exists: fresh successor kits only")
e4.mkdir(parents=True)
KEEP = ["boundary_guard_context.json", "clock_family.tcl", "constraint.sdc", "core.json", "corners.tcl", "drv.tcl",
        "face_flops.tcl", "face_flops_release.tcl", "face_guard_core.py", "face_guard_skip.txt", "face_keep.tcl",
        "face_keep_release.tcl", "hold_budget.tcl", "io.tcl", "macro_place.tcl", "make_tracks.tcl", "ot_keep_regs.tcl",
        "pair_skew.tcl", "pdn.tcl", "pin_audit.py", "pins.json", "pins_snapped.json", "post_grt_drv.tcl",
        "tap_balance.tcl", "checked_core_runner.py", "config.mk", "cts_post.tcl", "sdc_lint.json", "run_kit.sh"]
for f in KEEP:
    shutil.copy2(e3 / f, e4 / f)
shutil.copytree(e3 / "macros", e4 / "macros")
# RTL: same file list as E3, sources from the current tree
(e4 / "rtl").mkdir()
idx = {}
for p in (repo / "rtl").rglob("*"):
    if p.suffix in (".sv", ".v"):
        idx.setdefault(p.name, []).append(p)
rtl_src = {}
for f in sorted(x.name for x in (e3 / "rtl").iterdir()):
    c = idx.get(f, [])
    same = [p for p in c if p.read_bytes() == (e3 / "rtl" / f).read_bytes()]
    if not c and f.endswith("_bb.v"):
        # macro black-box stubs are not under rtl/ (physical/asap7_memory_macros*): macros unchanged, keep E3's copy
        shutil.copy2(e3 / "rtl" / f, e4 / "rtl" / f)
        rtl_src[f] = "E3 kit copy (macro black box, unchanged)"
        continue
    if len(c) == 1:
        src = c[0]
    elif same:
        src = same[0]
    else:
        raise SystemExit(f"rtl {f}: {len(c)} candidates and none equal to E3: {c}")
    shutil.copy2(src, e4 / "rtl" / f)
    rtl_src[f] = str(src.relative_to(repo))
# tools from the current tree
for f in ("signoff.py", "sdc_lint.py", "face_guard.py", "rtl_lint.py", "lec.py"):
    shutil.copy2(TOOL / f, e4 / f)
for f in ("macro_pin_flops.tcl", "macro_pin_flops_release.tcl", "anchor_row_packing.tcl"):
    shutil.copy2(CF / f, e4 / f)
for f in ("core_density_taps.tcl", "core_tap_align.tcl"):
    shutil.copy2(HB / f, e4 / f)
for f in ("rst_pin_regs.tcl", "rst_pin_regs_release.tcl"):
    shutil.copy2(HERE / f, e4 / f)
(e4 / "gpl_hooks.tcl").write_text("# PATH-S81/E4 PRE_GLOBAL_PLACE: face pin registers, reset pin registers, macro-pin flops (incl. ROM CPRE captures)\n"
                                  "source /work/face_flops.tcl\nsource /work/rst_pin_regs.tcl\nsource /work/macro_pin_flops.tcl\n")
(e4 / "dpl_hooks.tcl").write_text("# PATH-S81/E4 PRE_DETAIL_PLACE: release all anchors to PLACED for DPL\n"
                                  "source /work/face_flops_release.tcl\nsource /work/rst_pin_regs_release.tcl\nsource /work/macro_pin_flops_release.tcl\n")
(e4 / "pre_cts.tcl").write_text("# PATH-S81/E4 PRE_CTS: repair buffer budget (E3 hold_budget.tcl), then the MSCTS density taps\n"
                                "source /work/hold_budget.tcl\nsource /work/core_density_taps.tcl\n")
cp = (e4 / "cts_post.tcl").read_text()
assert cp.count("repair_timing_helper\n") == 1
(e4 / "cts_post.tcl").write_text(cp.replace("repair_timing_helper\n", "# modern flow: setup-only here; hold is repaired only in the FF frame (FF-only GRT step)\nrepair_timing_helper -setup\n"))
# FLOW core_flow: per-corner vclk + RCX RC; the kit's own GRT hooks chained
b = core_flow.binding(250.0, 202.5, 40.0, basis_tt="plan clock 250 (E3 constraint.sdc)", basis_ff="FLOW 0.81 x TT")
flow_cfg = core_flow.apply(e4, b, "dsdv_eng_rr_e", time_unit_ps=1.0, rc_cal=True, hold_ff_margin=5.0,
                           grt_pre_extra=["/work/drv.tcl", "/work/hold_budget.tcl"], grt_post_extra=["/work/post_grt_drv.tcl"])
sl = json.loads((e4 / "sdc_lint.json").read_text()); sl["insertion_ff_ps"] = 202.5
(e4 / "sdc_lint.json").write_text(json.dumps(sl, indent=1) + "\n")
rk = (e4 / "run_kit.sh").read_text()
anchor = "  if [ \\$rc = 0 ]; then \\$M $GOAL; rc=\\$?; fi; \\\n"
assert rk.count(anchor) == 1, "run_kit.sh goal anchor"
rk = rk.replace(anchor, "  " + core_flow.FF_GRT_STEP + "\\\n" + anchor)
(e4 / "run_kit.sh").write_text(rk)
cfg = (e4 / "config.mk").read_text()
cfg = cfg.replace("# PATH-S81/ENG E3 2026-10-25:", "# PATH-S81/E4 2026-10-25: E3 + OHSEL + BF_PREDEC + ROM capture anchors + density taps + reset pin regs + FLOW per-corner vclk. E3 header:", 1)
cfg = cfg.replace("DESIGN_NICKNAME = kr_dsdv_eng_rr_e_e3", "DESIGN_NICKNAME = kr_dsdv_eng_rr_e_e4")
cfg = cfg.replace("-DOT_S81ENG_TMAP_CPRE\n", "-DOT_S81ENG_TMAP_CPRE -DOT_S81ENG_XQ_OHSEL -DOT_S81ENG_BF_PREDEC\n")
for k, v in (("PRE_GLOBAL_PLACE_TCL", "/work/gpl_hooks.tcl"), ("PRE_DETAIL_PLACE_TCL", "/work/dpl_hooks.tcl"),
             ("PRE_CTS_TCL", "/work/pre_cts.tcl"), ("POST_CTS_TCL", "/work/core_tap_align.tcl")):
    cfg, n = re.subn(rf"^export {k} = .*$", f"export {k} = {v}", cfg, flags=re.M)
    assert n == 1, k
cfg, n = re.subn(r"^export CTS_ARGS = .*$", "export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 "
                 "-sink_clustering_max_diameter 30 -sink_clustering_size 20 -distance_between_buffers 40 -balance_levels", cfg, flags=re.M)
assert n == 1
cfg = cfg.rstrip("\n") + "\n" + "\n".join([
    "# PATH-S81/E4 F6: ROM CPRE capture anchors (DFFE enable-feedback walk)", "export OT_MPF_ENMUX = 1",
    "# PATH-S81/E4 MSCTS density taps (owner 10-23 rule; <= 400 sinks / tap, 60 um regions), aligned <= 8 ps",
    "export OT_DTAP_PORT = ck", "export OT_DTAP_TARGET = 400", "export OT_DTAP_DMAX_UM = 60", "export OT_DTAP_OUT = /work/dtap.txt",
    "export OT_DTAP_NEXT = /work/cts_post.tcl", "export OT_RPR_PORTS = rst_n",
    "# FLOW-FIX 10-25 core_flow (LAST)"] + flow_cfg) + "\n"
(e4 / "config.mk").write_text(cfg)
for f in ("hold_budget.tcl",):
    assert (e4 / f).exists()
(e4 / "run_checked.sh").write_text((e3 / "run_checked.sh").read_text().replace("E3", "E4"))
(e4 / "run_checked.sh").chmod(0o755)
(e4 / "gate_synth.sh").write_text((e3 / "gate_synth.sh").read_text().replace("E3", "E4").replace("e3lint", "e4lint"))
(e4 / "gate_synth.sh").chmod(0o755)
(e4 / "gate_lec.sh").write_text((e3 / "gate_lec.sh").read_text().replace("E3", "E4").replace(
    "(incl. -DOT_S81ENG_TMAP_CPRE)", "(TMAP_CPRE + XQ_OHSEL + BF_PREDEC)").replace("main tools/die_plan/lec.py", "TOK-LEC lec.py (claude/tok-lec-0825)"))
(e4 / "gate_lec.sh").chmod(0o755)
fz = json.loads((e3 / "freeze.json").read_text())
fz.update(kit="dsdv_eng_rr_e_e4", predecessor=str(e3), rtl_sources=rtl_src,
          defines_added=["OT_S81ENG_XQ_OHSEL", "OT_S81ENG_BF_PREDEC"],
          physical=dict(rom_capture_anchor="macro_pin_flops.tcl OT_MPF_ENMUX=1", clock="core_density_taps 400/60um + core_tap_align",
                        reset="rst_pin_regs.tcl (rst_n root at the pin)", flow="core_flow per-corner vclk 250/202.5 + RCX RC"))
(e4 / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
print(json.dumps(dict(kit=str(e4), rtl=len(rtl_src))))
