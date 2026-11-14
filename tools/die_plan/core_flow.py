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
import re
import shutil
from pathlib import Path


def _common_flow_file(name, repo):
    """physical/common_flow/<name> of checkout `repo`, from git HEAD in a sparse checkout without it
    (common_flow_src.py, DIE-KV-62 11-02); a copy of this module without the helper: the plain path."""
    try:
        from common_flow_src import common_flow_file
    except ImportError:
        return Path(repo) / "physical/common_flow" / name
    return common_flow_file(name, repo)

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
HOLD_FF_MARGIN_DEFAULT = 0.0   # OWNER 11-02 (FLOW-22): no +10 ps hold margin; every hold gate is FF hold slack >= 0 (25 ps FF hold uncertainty stays); was 10 (12.19)

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
def runtime_mm_patch_step():
    """The SAME canonical MM patch step for a direct common runtime shell.

    Generator templates escape dollars for an enclosing bash -lc string;
    a standalone admitted CTS consumer needs the unescaped shell form.
    """
    return MM_PATCH_STEP.replace("\\$", "$")


# Actual Make evaluation preserves override/export precedence; blank retains the absent-margin path.
HOLD_MARGIN_READ = (
    'HM=; if [ \\$rc = 0 ]; then HMR=\\$(\\$M print-OT_HOLD_FF_MARGIN 2> /work/hold_margin_read.log); hmr=\\$?; '
    "if [ \\$hmr != 0 ]; then cat /work/hold_margin_read.log; echo 'FAIL_POSTCTS hold margin Make read' | tee -a /work/FAIL_POSTCTS; rc=9; "
    'else HM=\\$(printf \'%s\\\\n\' \\"\\$HMR\\" | sed -nE \'s/^OT_HOLD_FF_MARGIN[[:space:]]*[:=][[:space:]]*//p\'); '
    'if [ -n \\"\\$HM\\" ] && ! python3 -c \'import math,re,sys; s=sys.argv[1].strip(); valid=re.fullmatch(r\\"[+-]?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+)(?:[eE][+-]?[0-9]+)?\\",s); x=float(s) if valid else float(\\"nan\\"); sys.exit(not math.isfinite(x))\' \\"\\$HM\\" > /work/hold_margin_value.log 2>&1; then '
    'echo \\"FAIL_POSTCTS invalid OT_HOLD_FF_MARGIN [\\$HM]: expected a finite number\\" | tee -a /work/FAIL_POSTCTS; rc=9; fi; fi; fi; '
)

FF_GRT_STEP = (HOLD_MARGIN_READ +
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
HOLD_PAD_HB4 = Path(__file__).resolve().parents[2] / "physical" / "common_flow" / "hold_pad_hb4.tcl"
# CORE-MAXWIRE 11-09 (COORD LOOP-GAP 10:5x; HBM-COLLECT-1/PTW-C, S81 station405 slew class): type kits get a repeater
# pitch through gen.py phys --max-wire-um (grt_maxwire.tcl), core kits had none.  Every core kit now gets the same hook
# by default: the post-GRT repair_design adds -max_wire_length, CORE_MAXWIRE_UM_LOCAL on a core whose top routing
# layer is M7 or lower (local M2-M7 nets, slew set by repeater spacing), CORE_MAXWIRE_UM_HOP where M8/M9 hops exist
# (METHODOLOGY 450-um hop pitch).  Picked at make time from the kit's final MAX_ROUTING_LAYER (platform default M7).
# A kit that sets OT_MAXWIRE_UM itself keeps its value; "export OT_MAXWIRE_UM =" (empty) = off.  Clock nets untouched.
CORE_MAXWIRE_UM_LOCAL, CORE_MAXWIRE_UM_HOP = 80, 450
CORE_MAXWIRE_LINE = (f"export OT_MAXWIRE_UM ?= $(if $(filter M8 M9,$(MAX_ROUTING_LAYER)),"
                     f"{CORE_MAXWIRE_UM_HOP},{CORE_MAXWIRE_UM_LOCAL})")
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


LEAF_REPEAT_SRC, LEAF_REPEAT_KIT = "clk_leaf_repeat.tcl", "clk_leaf_repeat_default.tcl"
LAYOUT_RENDER_FILES = ("layout_render_hook.sh", "layout_render.tcl", "layout_smells.py")


def stage_grt183(kd):
    """FLOW-28 11-04: every kit carries the GRT-0183 fresh-process re-run its runner's make goes through (grt183_make.sh,
    grt183_resume.tcl, ROOT 10-15).  Inert unless an incremental GRT-0183 kills stage 5_1_grt.  KW-FIX-24: + the
    default-on clk_leaf_repeat (clk_leaf_repeat_default.tcl), which the same wrapper hooks into CTS and GRT."""
    for f in ("grt183_make.sh", "grt183_resume.tcl", "grt_stall_resume.tcl", "failfast_rules.py"):   # KW-FIX-17 11-05: + GRT-STALL resume; FAILFAST-1 11-11: + progress stops
        shutil.copyfile(_common_flow_file(f, TOOL.parents[1]), Path(kd) / f)
    # KW-FIX-24/LEAFREP 11-06 (COORD 20:0x (5) / 20:2x (6)): clk_leaf_repeat default-on.  grt183_make.sh (the make
    # wrapper above) sources this copy in the container's cts.tcl before POST_CTS (skipped when the kit hooks
    # clk_leaf_repeat.tcl itself) and in global_route.tcl after the first GRT parasitics estimate (long-branch pass).
    # Opt out per kit: 'export OT_CLK_LEAF_REPEAT = 0' (both) / 'export OT_CLK_LEAF_GRT = 0' (GRT pass) in config.mk.
    shutil.copyfile(_common_flow_file(LEAF_REPEAT_SRC, TOOL.parents[1]), Path(kd) / LEAF_REPEAT_KIT)
    # KW-FIX-25/AUTORENDER 11-06 (OWNER visual check + smells): advisory layout PNGs + smells.json after place, GRT, route.
    # grt183_make.sh hooks flow.sh's exit; reads stage ODBs only, writes run/layout_review, never fails a run.
    # Opt out per kit: 'export OT_LAYOUT_RENDER = 0' in config.mk.
    for f in LAYOUT_RENDER_FILES:
        shutil.copyfile(_common_flow_file(f, TOOL.parents[1]), Path(kd) / f)


CLK_ROOT_CROSS_TCL, CLK_ROOT_CROSS_PY = "clk_root_cross.tcl", "clk_root_cross.py"
CLK_ROOT_CROSS_SOURCE = "source /work/clk_root_cross.tcl\n"


def stage_clk_root_cross(kd):
    """CLK-ROOT-CROSS (DIE-HBM-97 11-10, COORD vecd-clkroot-gen): stage the root-repeater pass for clock ports boxed in
    by macros (physical/common_flow/clk_root_cross.tcl + tools/die_plan/clk_root_cross.py) and return the line the
    generator puts FIRST in its PRE_GLOBAL_ROUTE hook.  Geometry decides per port net at run time; a kit where no port
    is boxed in gets no cell.  Opt out per kit: 'export OT_CLK_ROOT_CROSS = 0' in config.mk."""
    shutil.copyfile(_common_flow_file(CLK_ROOT_CROSS_TCL, TOOL.parents[1]), Path(kd) / CLK_ROOT_CROSS_TCL)
    shutil.copyfile(TOOL / CLK_ROOT_CROSS_PY, Path(kd) / CLK_ROOT_CROSS_PY)
    return CLK_ROOT_CROSS_SOURCE


# KW-FIX-24/LEAFOPT 11-06 (COORD 21:0x (1)): a kit whose plan owns the whole clock tree (S81 regional-tap kits, HBM /
# S81 plan-built core trees with a planned spine; core_infra.kit_cts_hook) opts out of the default-on clk_leaf_repeat
# through its generator.  Every other kit keeps the default.
LEAF_REPEAT_OPTOUT = "export OT_CLK_LEAF_REPEAT = 0"
_LEAF_REPEAT_SET = re.compile(r"^\s*(override\s+)?export\s+OT_CLK_LEAF_REPEAT\s*[:?]?=")


def leaf_repeat_plan_optout(cfg, why):
    """Append the clk_leaf_repeat opt-out (with a comment naming why) to config.mk lines cfg, in place, unless cfg
    already sets OT_CLK_LEAF_REPEAT (a kit / recipe choice wins).  -> True when the line was added."""
    if any(_LEAF_REPEAT_SET.match(str(ln)) for ln in cfg):
        return False
    cfg += [f"# KW-FIX-24/LEAFOPT (COORD 21:0x): {why}: the plan owns the whole clock tree -> no default clk_leaf_repeat",
            LEAF_REPEAT_OPTOUT]
    return True


def apply(kd, b, design, time_unit_ps=1.0, rc_cal=True, hold_ff_margin=HOLD_FF_MARGIN_DEFAULT, grt_pre_extra=(),
          grt_post_extra=(), grt_nonport_hold=False):
    """copy the flow helpers into kit dir kd and return the config.mk lines (FLOW defaults).  grt_pre_extra /
    grt_post_extra: kit Tcl files (under /work) the generator's own PRE/POST_GLOBAL_ROUTE hooks used to be (they are
    chained after main's grt_pre.tcl / grt_post.tcl in a generated grt_pre_core.tcl / grt_post_core.tcl).
    grt_nonport_hold opts a NEW kit into the shared input-start exclusion during FF GRT repair only;
    TT setup and final full-path sign-off are unchanged. Default keeps the original generated files."""
    kd = Path(kd)
    shutil.copyfile(TOOL.parent / "orfs_hold_mm.py", kd / "orfs_hold_mm.py")
    stage_grt183(kd)
    for f in ("rtl_lint.py", "vclk_corner.tcl", "grt_pre.tcl", "grt_maxwire.tcl", "hold_guard_grt.tcl","grt_layers.tcl", "grt_post.tcl", "pg_track_truth.tcl", "pg_connect.tcl", "unplaced_setup_guard.tcl", "native_cell_cap.tcl") + KIT_MODE_FILES:
        shutil.copyfile(TOOL / f, kd / f)
    # KIT-TRIAGE-1/G5 11-01 (COORD 05:0x: extend the HBM-CORES-KITS-40 HB4 hook b26a827db45 to the S81 / KV / QC core
    # kits as one class form): every core kit's FF GRT hold repair may pad with HB4xp67 (physical/common_flow/
    # hold_pad_hb4.tcl: dont_use lifted ONLY inside repair_timing -hold, idempotent per process).  exp0: BUFx2 guarded
    # chunks stalled at FF hold -25.87, HB4 -86.36 -> +0.94 / 0 viol.  Same constraints, margins and acceptance.
    shutil.copyfile(_common_flow_file(HOLD_PAD_HB4.name, HOLD_PAD_HB4.parents[2]), kd / "hold_pad_hb4.tcl")
    shutil.copyfile(TOOL / "core_final_repair.tcl", kd / "core_final_repair.tcl")
    # TYPE-SAFE-1 11-06 (COORD RULINGS 19:0x (3)): every core kit balances its clock subtrees on GRT RC after all
    # post-GRT kit hooks and BEFORE the final TT/FF repair (subtree_balance.tcl; kit config OT_STB=0 opts out)
    shutil.copyfile(TOOL / "subtree_balance.tcl", kd / "subtree_balance.tcl")
    pre = ["# GENERATED by tools/die_plan/core_flow.py: main grt_pre.tcl (FF vclk binding) then the kit's own hook(s)",
           "source /work/grt_pre.tcl"] + [f"source {x}" for x in grt_pre_extra] + \
          ["source /work/hold_pad_hb4.tcl"] + GRT_BUFFER_CAP.splitlines()
    if grt_nonport_hold:
        # Install after HB4 and buffer-cap wrappers, as required by the shared adapter.
        shutil.copyfile(TOOL.parent / "grt_nonport_hold.tcl", kd / "grt_nonport_hold.tcl")
        pre.append("source /work/grt_nonport_hold.tcl")
    post = ["# GENERATED by tools/die_plan/core_flow.py: the kit's own hook(s), then main grt_post.tcl (vclk back to TT)"]
    post += [f"source {x}" for x in grt_post_extra] + ["source /work/grt_post.tcl",
                                                             "source /work/subtree_balance.tcl",
                                                             "source /work/core_final_repair.tcl"]
    (kd / "grt_pre_core.tcl").write_text("\n".join(pre) + "\n")
    (kd / "grt_post_core.tcl").write_text("\n".join(post) + "\n")
    (kd / "pre_floorplan_core.tcl").write_text(
        '# Measure the actual native top before floorplan work, then preserve generator hooks.\n'
        'source /work/native_cell_cap.tcl\n'
        'if {[info exists ::env(OT_CORE_PRE_FLOORPLAN_TCL)]} {\n'
        '  foreach hook $::env(OT_CORE_PRE_FLOORPLAN_TCL) { source $hook }\n'
        '}\nsource /work/unplaced_setup_guard.tcl\n')
    cfg = [f"export OT_VCLK_TT = {b['tt'] / time_unit_ps:.4f}",
           f"export OT_VCLK_FF = {b['ff'] / time_unit_ps:.4f}",
           f"export OT_HOLD_FF_MARGIN = {hold_ff_margin:g}",
           "export OT_CORE_PRE_FLOORPLAN_TCL := $(PRE_FLOORPLAN_TCL)",
           "export PRE_FLOORPLAN_TCL = /work/pre_floorplan_core.tcl",
           "override export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre_core.tcl",
           "override export POST_GLOBAL_ROUTE_TCL = /work/grt_post_core.tcl",
           CORE_MAXWIRE_LINE]
    if grt_nonport_hold:
        cfg.append("export OT_GRT_NONPORT_HOLD = 1")
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
