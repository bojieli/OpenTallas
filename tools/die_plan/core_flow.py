"""core_flow: main's kit-flow defaults for kit generators that do not go through gen_phys (HBM / KV / QC hard-core
generators).  FLOW-FIX 2026-10-25 (flow-canary findings F1 + F2, COORD per-corner insertion add-on).

  F1  pre-synthesis RTL lint (rtl_lint.py: implicit / undriven nets, missing modules or ports) as the first
      run-script step: FAIL_PREFLOOR lint, rc 8 (gen_phys RUN_KIT exit code).
  F2  placement / CTS / GRT parasitic estimates on the ASAP7 per-layer RC calibrated to routed RCX
      (setRC_rcx_asap7.tcl copied as setRC_rcx.tcl).  The asap7lock image reads LAYER_PARASITICS_FILE and ignores
      SET_RC_TCL, so both are exported (as gen_phys).
  I   per-corner insertion binding (METHODOLOGY 9.7 / BRIEFING 5e, main 9f716b354): the IO virtual clock stands for
      the neighbour's face flop, whose insertion tracks the corner.  constraint.sdc carries the bound TT value;
      config.mk exports OT_VCLK_TT / OT_VCLK_FF (SDC time units); the FF-only GRT hold repair step
      (OT_VCLK_CORNER=ff make grt CORNER=BC CORNERS=bc) binds the FF value through grt_pre.tcl / vclk_corner.tcl and
      grt_post.tcl restores TT; clock_binding.json records the values + basis.  No more fixed plan-latency vclk for
      both corners.

Generators call binding() + apply(); their run scripts embed LINT_STEP first and FF_GRT_STEP before the main make
goal (both are fragments of a `bash -lc "..."` string: $ and " are escaped as in gen_phys.RUN_KIT).
"""
import json
import shutil
from pathlib import Path

TOOL = Path(__file__).resolve().parent
FF_TT_INSERTION_RATIO = 0.81   # gen_phys.FF_TT_INSERTION_RATIO: routed RCX FF/TT pin-register mean ratio
RC_CAL_FILE, RC_CAL_KIT = "setRC_rcx_asap7.tcl", "setRC_rcx.tcl"
RC_CAL_LAYERS = ("M2", "M3", "M4", "M5", "M6", "M7")


def check_rc_cal(path):
    """FLOW-RC-1 (2026-10-27) fail-closed guard: a kit RC file must carry a SIGNAL-net and a CLOCK-net calibration.
    Required: '# OT_RC_CAL signal <basis>' and '# OT_RC_CAL clock <basis>' records, 'set_wire_rc -signal' and
    'set_wire_rc -clock' (placement-stage per-class RC) and 'set_layer_rc -layer' for every routing layer M2-M7
    (GRT / estimate basis).  Raises SystemExit('RC_CAL_GUARD ...') otherwise; returns the parsed records."""
    import re
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"RC_CAL_GUARD missing RC calibration file {path}")
    txt = path.read_text()
    rec = dict(re.findall(r"^#\s*OT_RC_CAL\s+(signal|clock)\s+(\S.*)$", txt, re.M))
    miss = [k for k in ("signal", "clock") if k not in rec]
    miss += [f"set_wire_rc -{k}" for k in ("signal", "clock")
             if not re.search(rf"^set_wire_rc\s+-{k}\s+-resistance\s+\S+\s+-capacitance\s+\S+", txt, re.M)]
    miss += [f"set_layer_rc {L}" for L in RC_CAL_LAYERS
             if not re.search(rf"^set_layer_rc\s+-layer\s+{L}\s+-resistance\s+\S+\s+-capacitance\s+\S+", txt, re.M)]
    if miss:
        raise SystemExit(f"RC_CAL_GUARD {path}: no {', '.join(miss)} (a kit without a signal-net RC calibration fails "
                         "closed; FLOW-RC-1)")
    return rec


def install_rc(kd, src=None):
    """copy the shared calibrated RC file into kit dir kd as setRC_rcx.tcl after check_rc_cal (every generator)."""
    src = Path(src) if src else TOOL / RC_CAL_FILE
    check_rc_cal(src)
    shutil.copyfile(src, Path(kd) / RC_CAL_KIT)
    return check_rc_cal(Path(kd) / RC_CAL_KIT)
LINT_RC = 8
# FLOW-HOLD-1 (OWNER 12.19, COORD 10-29 05:52): default FF hold repair margin of every NEW kit = 10 ps (was 5 here, 0 in
# several die generators).  A lane may raise it to 15 where a measured GRT->final RC hold loss > 10 ps is documented
# (QC btab, HBM ring).  Already SIGNED views stay valid (new builds only).  gen_phys / gen.py / the die core generators
# take this constant as their default.
HOLD_FF_MARGIN_DEFAULT = 10.0

# first step inside the docker bash -lc string (rc starts at 0 before it)
LINT_STEP = ("python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1; rc=\\$?; "
             "tail -3 /work/rtl_lint.log; if [ \\$rc != 0 ]; then echo 'FAIL_PREFLOOR lint (implicit / undriven nets, "
             "missing module or port; or NOT RUN), see rtl_lint.json' | tee -a /work/FAIL_PREFLOOR; rc=8; fi; ")

# FF-only GRT hold repair in the FF vclk frame before the main goal (goals that reach GRT: finish / route / grt); the
# following `make <goal>` resumes from 5_1_grt (a no-op for goal grt).  OT_HOLD_FF_MARGIN unset (or OT_VCLK_FF unset) =
# step skipped.  S81-CORE-LAT-R18 (CHECKED l0 c16 4_1_cts probe): goal grt used to skip this step, so `make grt` ran
# the kit's tc+bc session with the ONE SDC vclk latency (TT 250) and repaired FF hold against the TT vclk: FF IO hold
# -23.5 ps on 1759 endpoints with vclk 250 vs 15 endpoints with the FF vclk 202.5 -> RSZ-0060 after 3690 buffers.
# CLOCK-RESET 2026-10-25 (KV core canary TT -222.85): `make grt` builds every missing prerequisite, so without a
# prior `make cts` floorplan / place resize / CTS repair_timing all ran with CORNERS=bc (FF libraries only) and TT
# setup was never repaired before the sign-off TT STA.  `\$M cts` (the kit's own CORNER / CORNERS, a no-op when
# 4_cts.odb is current) first, so only the 5_1_grt step runs in the FF frame.
# SIGNOFF-MODES-2 2026-10-27: ONE TIMING MODE PER CORNER (tools/die_plan/kit_modes.py, copied into every kit).
#   * CTS (kit corners): a single-mode tc+bc CTS hold repair (FF hold timed against the TT vclk) is reported
#     ADVISORY (QoR: the FF-frame GRT step and the per-corner sign-off measure the result); OT_KIT_MODES_STRICT=1
#     in config.mk makes it fail closed (rc 9).
#   * GRT: FF-only session (CORNER=BC CORNERS=bc, OT_VCLK_CORNER=ff -> vclk = OT_VCLK_FF), or -- for a kit staged
#     two-mode (kit_modes.py stage: OT_HOLD_MM=1, scene tc TT setup vclk OT_VCLK_TT / scene BC FF hold vclk_ff.sdc)
#     -- the kit's own two-mode session with no OT_VCLK_CORNER.  kit_modes.py checks the session and the TT/FF vclk
#     binding first and FAILS CLOSED (rc 9).  MM_PATCH_STEP patches the disposable ORFS container for staged kits.
MODES_CHECK = "python3 -I /work/kit_modes.py check /work"
MM_PATCH_STEP = ("if [ \\$rc = 0 ] && grep -q '^override export OT_HOLD_MM = 1' /work/config.mk; then "
                 "python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl "
                 "> /work/orfs_hold_mm.log 2>&1 || { cat /work/orfs_hold_mm.log; echo 'KIT_MODES FAIL orfs_hold_mm patch'; rc=9; }; fi; ")
FF_GRT_STEP = ("HM=\\$(sed -n 's/^export OT_HOLD_FF_MARGIN = //p' /work/config.mk); "
               "VF=\\$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk); "
               "MM=\\$(grep -c '^override export OT_HOLD_MM = 1' /work/config.mk); "
               "if [ \\$rc = 0 ] && [ -n \\\"\\$HM\\\" ] && [ -n \\\"\\$VF\\\" ] && { [ $GOAL = finish ] || [ $GOAL = route ] || [ $GOAL = grt ]; }; "
               f"then {MODES_CHECK} --step cts > /work/kit_modes_cts.log 2>&1; km=\\$?; cat /work/kit_modes_cts.log; "
               "if [ \\$km != 0 ]; then if grep -q '^export OT_KIT_MODES_STRICT = 1' /work/config.mk; then "
               "echo 'FAIL_PREFLOOR kit_modes cts (one timing mode per corner, strict)' | tee -a /work/FAIL_PREFLOOR; rc=9; "
               "else echo 'KIT_MODES ADVISORY cts: hold repaired in a single mode over tc+bc (QoR only)'; fi; fi; fi; "
               + MM_PATCH_STEP +
               "if [ \\$rc = 0 ] && [ -n \\\"\\$HM\\\" ] && [ -n \\\"\\$VF\\\" ] && { [ $GOAL = finish ] || [ $GOAL = route ] || [ $GOAL = grt ]; }; "
               "then \\$M cts; rc=\\$?; if [ \\$rc != 0 ]; then echo 'CTS (kit corners) before the FF-only GRT step failed'; fi; fi; "
               "if [ \\$rc = 0 ] && [ -n \\\"\\$HM\\\" ] && [ -n \\\"\\$VF\\\" ] && [ \\$MM != 0 ] && { [ $GOAL = finish ] || [ $GOAL = route ] || [ $GOAL = grt ]; }; "
               f"then {MODES_CHECK} --step grt --session 'tc bc' --hold-repair || rc=9; "
               "if [ \\$rc = 0 ]; then \\$M grt HOLD_SLACK_MARGIN=\\$HM; rc=\\$?; fi; "
               "if [ \\$rc != 0 ]; then echo 'per-mode GRT hold repair (tc TT setup / BC FF hold) failed'; fi; "
               "elif [ \\$rc = 0 ] && [ -n \\\"\\$HM\\\" ] && [ -n \\\"\\$VF\\\" ] && { [ $GOAL = finish ] || [ $GOAL = route ] || [ $GOAL = grt ]; }; "
               f"then {MODES_CHECK} --step grt --session bc --vclk-corner ff --hold-repair || rc=9; "
               "if [ \\$rc = 0 ]; then OT_VCLK_CORNER=ff \\$M grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=\\$HM; rc=\\$?; fi; "
               "if [ \\$rc != 0 ]; then echo 'FF-only GRT hold repair (FF vclk frame) failed'; fi; fi; ")
KIT_MODE_FILES = ("kit_modes.py", "kit_modes_eco.tcl")
# FLOW-KITFAIL-3 10-29 (S81 CRS4 ra2 RSZ-0060, fixed kit-local in ra3): the FF-only GRT hold repair runs through ORFS
# repair_timing_helper at OpenROAD's default 20 % buffer cap, below the demand of pin-fed bank flops (4519 flops fed
# straight from input pins at min input delay -40 ps on the FF vclk).  Same raise as hold_repair_pre.tcl (plan_demand
# kits): OT_MAX_BUFFER_PERCENT (default 100) lifts the tool cap only -- the cap is a stop limit (RSZ-0060), so a repair
# that stays under 20 % inserts exactly the same cells.  Margins, corners and constraints unchanged.
GRT_BUFFER_CAP = """# FLOW-KITFAIL-3: GRT repair_timing buffer cap (OT_MAX_BUFFER_PERCENT, default 100; OpenROAD default 20 = RSZ-0060)
set ::ot_grt_mbp [expr {[info exists ::env(OT_MAX_BUFFER_PERCENT)] && $::env(OT_MAX_BUFFER_PERCENT) ne "" ? $::env(OT_MAX_BUFFER_PERCENT) : 100}]
if {[llength [info procs ::repair_timing_helper]] && ![llength [info procs ::ot_grt_rth_orig]] && ![llength [info procs ::ot_hr_rth_orig]]} {
  rename ::repair_timing_helper ::ot_grt_rth_orig
  proc ::repair_timing_helper {args} {
    puts "OT_GRT_BUFFER_CAP repair_timing -max_buffer_percent $::ot_grt_mbp"
    ::ot_grt_rth_orig {*}$args -max_buffer_percent $::ot_grt_mbp
  }
}"""


def binding(tt_ps, ff_ps=None, tol_ps=40.0, basis_tt="plan clock", basis_ff=None):
    """{tt, ff, tol, basis}: bound pin-register insertion per corner (ps).  FF absent -> 0.81 x TT."""
    tt = float(tt_ps)
    if ff_ps is None:
        ff, bf = round(FF_TT_INSERTION_RATIO * tt, 1), f"FF_TT_INSERTION_RATIO {FF_TT_INSERTION_RATIO:g} x TT"
    else:
        ff, bf = float(ff_ps), basis_ff or basis_tt
    if not 0 < ff <= tt:
        raise ValueError(f"bound FF insertion {ff:g} ps must be in (0, TT {tt:g}]")
    return dict(tt=tt, ff=ff, tol=float(tol_ps), basis=dict(tt=basis_tt, ff=bf))


def apply(kd, b, design, time_unit_ps=1.0, rc_cal=True, hold_ff_margin=HOLD_FF_MARGIN_DEFAULT, grt_pre_extra=(),
          grt_post_extra=()):
    """copy the flow helpers into kit dir kd and return the config.mk lines (FLOW defaults).  grt_pre_extra /
    grt_post_extra: kit Tcl files (under /work) the generator's own PRE/POST_GLOBAL_ROUTE hooks used to be (they are
    chained after main's grt_pre.tcl / grt_post.tcl in a generated grt_pre_core.tcl / grt_post_core.tcl)."""
    kd = Path(kd)
    for f in ("rtl_lint.py", "vclk_corner.tcl", "grt_pre.tcl", "grt_post.tcl", "pg_connect.tcl") + KIT_MODE_FILES:
        shutil.copyfile(TOOL / f, kd / f)
    pre = ["# GENERATED by tools/die_plan/core_flow.py: main grt_pre.tcl (FF vclk binding) then the kit's own hook(s)",
           "source /work/grt_pre.tcl"] + [f"source {x}" for x in grt_pre_extra] + GRT_BUFFER_CAP.splitlines()
    post = ["# GENERATED by tools/die_plan/core_flow.py: the kit's own hook(s), then main grt_post.tcl (vclk back to TT)"]
    post += [f"source {x}" for x in grt_post_extra] + ["source /work/grt_post.tcl"]
    (kd / "grt_pre_core.tcl").write_text("\n".join(pre) + "\n")
    (kd / "grt_post_core.tcl").write_text("\n".join(post) + "\n")
    cfg = [f"export OT_VCLK_TT = {b['tt'] / time_unit_ps:.4f}",
           f"export OT_VCLK_FF = {b['ff'] / time_unit_ps:.4f}",
           f"export OT_HOLD_FF_MARGIN = {hold_ff_margin:g}",
           "override export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre_core.tcl",
           "override export POST_GLOBAL_ROUTE_TCL = /work/grt_post_core.tcl"]
    if rc_cal:
        install_rc(kd)
        cfg += [f"export LAYER_PARASITICS_FILE = /work/{RC_CAL_KIT}", f"export SET_RC_TCL = /work/{RC_CAL_KIT}"]
    (kd / "clock_binding.json").write_text(json.dumps(dict(
        type=design, insertion_ps=dict(tt=b["tt"], ff=b["ff"]), insertion_tol_ps=b["tol"], basis=b["basis"],
        rc=("calibrated " + RC_CAL_FILE) if rc_cal else "stock platform setRC.tcl",
        rule="METHODOLOGY 9.7 / BRIEFING 5e; FLOW 2026-10-25; FLOW-FIX core generators"), indent=1) + "\n")
    return cfg


ISLAND_GUARD_PRE = """# GENERATED by tools/die_plan/core_flow.py island_macro_guard (KV-CORES-R9 / COORD 10-27 11:1x): PRE_MACRO_PLACE.
# Plan clock-island rects (+ macro halo) become dbBlockages BEFORE rtl_macro_placer (mpl honours them), so no macro
# or macro halo lands on an island row (pv_pair R0 / ectlk_q0 OT_ISLAND_FT_NO_ROW).  PRE_TAPCELL removes exactly these
# blockages again (std cells and the fixed island cells must use the rows) after a fail-closed macro check.
set ::ot_isl_guard {%s}
set ::ot_isl_halo %s
set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
foreach r $::ot_isl_guard {
  lassign $r x0 y0 x1 y1
  odb::dbBlockage_create $b [expr {round(($x0 - $::ot_isl_halo) * $u)}] [expr {round(($y0 - $::ot_isl_halo) * $u)}] \
      [expr {round(($x1 + $::ot_isl_halo) * $u)}] [expr {round(($y1 + $::ot_isl_halo) * $u)}]
}
puts "OT_ISLAND_MACRO_GUARD [llength $::ot_isl_guard] island rects blocked for macro placement (halo $::ot_isl_halo um)"
"""
ISLAND_GUARD_POST = """# GENERATED by tools/die_plan/core_flow.py island_macro_guard: PRE_TAPCELL = check + remove the PRE_MACRO_PLACE blockages.
source /work/island_macro_guard_pre_vars.tcl
set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
set want {}
foreach r $::ot_isl_guard {
  lassign $r x0 y0 x1 y1
  lappend want [list [expr {round(($x0 - $::ot_isl_halo) * $u)}] [expr {round(($y0 - $::ot_isl_halo) * $u)}] \
      [expr {round(($x1 + $::ot_isl_halo) * $u)}] [expr {round(($y1 + $::ot_isl_halo) * $u)}]]
}
foreach i [$b getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set q [$i getBBox]
  foreach r $::ot_isl_guard w $want {
    lassign $w x0 y0 x1 y1
    if {[$q xMin] < $x1 && [$q xMax] > $x0 && [$q yMin] < $y1 && [$q yMax] > $y0} {
      error "OT_ISLAND_MACRO macro [$i getName] over island $r + halo $::ot_isl_halo"
    }
  }
}
set n 0
foreach k [$b getBlockages] {
  set q [$k getBBox]
  if {[lsearch -exact $want [list [$q xMin] [$q yMin] [$q xMax] [$q yMax]]] >= 0} { odb::dbBlockage_destroy $k; incr n }
}
if {$n != [llength $want]} { error "OT_ISLAND_MACRO_GUARD removed $n of [llength $want] guard blockages" }
puts "OT_ISLAND_MACRO_GUARD PASS: no macro over [llength $want] island rects + halo; $n guard blockages removed"
"""


def island_macro_guard(kd, rects, halo_um):
    """KV-CORES-R9: plan clock-island rects (core frame um) -> PRE_MACRO_PLACE dbBlockages (+halo) for rtl_macro_placer and
    a PRE_TAPCELL fail-closed check + removal.  Returns the config.mk lines; [] without rects."""
    kd = Path(kd)
    rects = [[float(v) for v in r] for r in rects]
    if not rects:
        return []
    lst = " ".join("{%s}" % " ".join(f"{v:g}" for v in r) for r in rects)
    (kd / "island_macro_guard_pre_vars.tcl").write_text(
        f"set ::ot_isl_guard {{{lst}}}\nset ::ot_isl_halo {halo_um:g}\n")
    (kd / "island_macro_guard_pre.tcl").write_text(ISLAND_GUARD_PRE % (lst, f"{halo_um:g}"))
    (kd / "island_macro_guard_post.tcl").write_text(ISLAND_GUARD_POST)
    (kd / "island_macro_guard.json").write_text(json.dumps(dict(
        schema="opentallas.island_macro_guard.v1", rects_um=rects, halo_um=halo_um,
        rule="COORD 10-27: island rects (+halo) are macro blockages before rtl_macro_placer; PRE_TAPCELL check"), indent=1) + "\n")
    return ["export PRE_MACRO_PLACE_TCL = /work/island_macro_guard_pre.tcl",
            "export PRE_TAPCELL_TCL = /work/island_macro_guard_post.tcl"]
