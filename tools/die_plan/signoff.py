#!/usr/bin/env python3
"""Uniform sign-off of a closed block (lane SIGNOFF, 2026-10-24): one recipe applied to every block before it is
called closed.  Past "closed" records came from many lanes and flows: some were not die-bindable (pin-flop spread
> 80 ps), kit SDCs before main 4b7b2b3e64 waived the sender seam hold (no set_output_delay -min), and 27 of 43 tiles
once "closed" were unassemblable (docs/LESSONS_ARCH_PHYSICAL_1012.md).  This tool re-signs a block from its ROUTED
data only, with the same checks for everyone.

    signoff.py run (--run-dir ORFS_RUN | --base RESULTS_BASE) [--kit KITDIR] [--sdc SDC] [--name N] --out DIR
                   [--corners ss,ff,tt] [--image IMG] [--insertion-target PS] [--record gate_result.json]
    signoff.py verdict DIR/signoff.json           # re-evaluate a record (exit 0 SIGNED, 1 NOT SIGNED)

INPUTS: the routed ODB (<base>/6_final.odb, else <base>/5_route.odb of a GOAL=route kit) and its SPEF
(<base>/6_final.spef with 6_final.odb; when absent the parasitics are
re-extracted with OpenRCX: extract_parasitics -ext_model_file asap7 rcx_patterns.rules, recorded as 'rcx').  The
golden SDC is the kit's constraint.sdc (KIT = parent of the ORFS run dir) unless --sdc; else <base>/6_final.sdc.
Macro / hard-child liberty files come from the kit config.mk ADDITIONAL_LIBS (/work = KIT), per corner (_ss/_ff/_tt).

ENGINE: OpenSTA as built into OpenROAD in the pinned ORFS image (openroad/orfs:latest = :asap7lock), one process per
corner (MCMM = TT + FF (+ SS for information with --corners tt,ff,ss) x 1 functional mode, run in parallel), ASAP7 NLDM
the exact TC/BC_LIB_FILES selected by the routed kit make configuration, including macro views.

CORNER RULE (owner, restated 2026-10-24, AGENTS.md c7ce2ed69a; supersedes the 2026-09-30 SS rule): timing closes at the
TYPICAL corner -- setup at TT, hold at FF, 60 / 25 ps uncertainty, related flop-pair skew with CPPR <= 80 ps (spread is INFO).  SS never gates; with
--corners ...,ss it is reported for information only.

CHECKS (each PASS / FAIL / NOT RUN; SIGNED only if every blocking check PASSes):
  setup_tt      TT setup WNS >= 0 with the SDC's 60 ps setup uncertainty (AGENTS.md 2026-10-24)        blocking
  hold_ff       FF hold WNS >= 0 under the STANDARD boundary-hold overlay                                  blocking
                (set_output_delay -min 0 and set_input_delay -min -insertion_tol (40 ps) on every data port vs the
                IO virtual clock: the 4b7b2b3e64 kit standard; the raw-SDC hold is reported as hold_ff_sdc)
  ss            SS setup / hold, only with --corners ...,ss: information, never a reason                 report
  uncertainty   the SDC carries 60 ps setup / 25 ps hold (sdc_lint 'uncertainty'), period = 833 ps     (in sdc_lint)
  drv           max transition and max capacitance violations = 0 at TT and FF (liberty limits; SS info)  blocking
  fanout        nets with fanout > FANOUT_MAX (64; ASAP7 liberty has no max_fanout)                        WARN only
  unconstrained check_setup -unconstrained_endpoints = 0, no unclocked registers, no loops                blocking
  clock         per corner: active-edge clock arrival at every register clock pin (insertion min/mean/max) and
                at the PIN FLOPS (registers whose D is in the fan-out of a data input or whose Q reaches a data
                output); related flop-pair skew with CPPR <= 80 ps at TT and FF (owner decision 5); spread INFO; with
                --insertion-target the pin-flop mean must be within +-insertion_tol (a hard-core kit whose core.json
                carries clock_contract.kind = hard_core_latency publishes its measured insertion instead:
                signoff.json core_latency; the target applies at the parent partition tap, COORD 10-24)     blocking
  sdc_lint      tools/die_plan/sdc_lint.py on the golden SDC (kit sdc_lint.json when present, else a context derived
                from the SDC + the routed netlist's ports with the plan period / insertion / tolerance)     blocking
  face_guard    tools/die_plan/face_guard.py on the synthesized netlist (<base>/1_synth.v | 1_2_yosys.v), with
                the kit pins.json when present                                                              blocking
  drc           routed DRC count = 0 (ORFS 5_2_route.json detailedroute__route__drc_errors, else the record /
                5_route_drc.rpt)                                                                            blocking
  antenna       antenna violating nets = 0 (5_2_route.json detailedroute__antenna__violating__nets)         blocking

OCV / DERATES: the verdict applies NO timing derate: the AGENTS.md 60 / 25 ps clock uncertainty is the project's
on-chip-variation + jitter margin (user decision 2026-09-30) and changing it needs an owner decision.  For visibility
each corner also reports the worst slack under a flat +-5 % OCV derate (late 1.05 / early 0.95, cell + net, data +
clock) as `ocv5_*` (information only, never a reason).  One SPEF (the flow's RCX, single ASAP7 rules file) serves all
three corners.
"""
import argparse
import concurrent.futures as cf
import datetime
import gzip
import json
import os
import math
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1] if len(HERE.parents) > 1 else HERE  # standalone /work kit copy
sys.path.insert(0, str(HERE))

SCHEMA = "opentallas.signoff.v1"
IMAGE = os.environ.get("ORFS_IMAGE", "openroad/orfs:latest")
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
PERIOD_PS = 833.0
UNC_SETUP_PS, UNC_HOLD_PS = 60.0, 25.0
INSERTION_PS, INSERTION_TOL_PS = 250.0, 40.0
PAIR_SKEW_MAX_PS = 80.0
# IO virtual-clock reference: 'sdc' (kit SDC value), 'pin-flop-mean' (FF only, opt-in with a contract), 'rebind'
# (FLOW 10-25, default for kits with a per-corner insertion binding: TT and FF each rebound to their routed pin-register
# mean, clock check FAILs when a mean is more than the tolerance from the bound value)
VCLK_MODES = ("sdc", "pin-flop-mean", "rebind", "bound-ff")
PAIR_VERIFY_TOL_PS = 1.0             # credited path-end skew vs CK-arrival skew - CPPR (integrity check)
PAIR_CREDIT_MAX = 5000                 # exact-credit path searches per check before the worst becomes a bound
SPREAD_MAX_PS = PAIR_SKEW_MAX_PS  # legacy record field; spread is information only
FANOUT_MAX = 64
SPREAD_CORNERS = ("tt", "ff")
CORNERS = ("tt", "ff")                 # the sign-off corners; "ss" may be added for information
ALL_CORNERS = ("tt", "ff", "ss")
BLOCKING = ("setup_tt", "hold_ff", "drv", "unconstrained", "clock", "sdc_lint", "face_guard", "drc", "antenna")


# ---- discovery ----------------------------------------------------------------------------------------------------
ROUTED_DBS = ("6_final.odb", "5_route.odb")


def routed_db(base):
    """the routed ODB of a results base: 6_final.odb, else 5_route.odb (kits run with GOAL=route), else None"""
    return next((n for n in ROUTED_DBS if (Path(base) / n).is_file()), None)


def find_base(run_dir):
    """<run>/results/asap7/<design>/base (exactly one) or run_dir itself if it holds a routed ODB."""
    rd = Path(run_dir)
    if routed_db(rd):
        return rd
    for pat in ("results/asap7/*/base", "run/results/asap7/*/base", "work/orfs/results/asap7/*/base"):
        hits = sorted(p for p in rd.glob(pat) if routed_db(p))
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise SystemExit(f"signoff: several routed bases under {rd}: {hits}")
    raise SystemExit(f"signoff: no results/asap7/*/base/{{6_final,5_route}}.odb under {rd}")


def orfs_root(base):
    """ORFS work dir (holds results/ logs/ reports/) of a results base."""
    b = Path(base).resolve()
    if b.name == "base" and b.parent.parent.name == "asap7" and b.parent.parent.parent.name == "results":
        return b.parent.parent.parent.parent
    return None


def discover(base, kit=None, sdc=None, record=None):
    base = Path(base).resolve()
    root = orfs_root(base)
    design = base.parent.name if root else None
    if kit is None and root is not None:
        for k in (root.parent, root.parent.parent, root.parent.parent.parent):
            if (k / "config.mk").is_file() and ((k / "constraint.sdc").is_file() or (k / "run").is_dir()):
                kit = k
                break
    kit = Path(kit).resolve() if kit else None
    d = dict(base=str(base), orfs=str(root) if root else None, design=design, kit=str(kit) if kit else None,
             odb=str(base / (routed_db(base) or "6_final.odb")), spef=None, sdc=None, sdc_source=None, synth=None, final_v=None,
             metrics={}, drc_rpt=None, pins=None, sdc_lint_ctx=None, record=str(record) if record else None)
    if (base / "6_final.spef").is_file() and Path(d["odb"]).name == "6_final.odb":
        d["spef"] = str(base / "6_final.spef")
    if sdc:
        d["sdc"], d["sdc_source"] = str(Path(sdc).resolve()), "arg"
    elif kit and (kit / "constraint.sdc").is_file():
        d["sdc"], d["sdc_source"] = str(kit / "constraint.sdc"), "kit"
    elif (base / "6_final.sdc").is_file():
        d["sdc"], d["sdc_source"] = str(base / "6_final.sdc"), "6_final.sdc"
    for n in ("1_synth.v", "1_2_yosys.v"):
        if (base / n).is_file():
            d["synth"] = str(base / n)
            break
    if (base / "6_final.v").is_file():
        d["final_v"] = str(base / "6_final.v")
    if root is not None:
        lg = root / "logs" / "asap7" / design / "base"
        for n in ("5_2_route.json", "5_1_grt.json", "6_report.json"):
            if (lg / n).is_file():
                try:
                    d["metrics"][n] = str(lg / n)
                except Exception:
                    pass
        r = root / "reports" / "asap7" / design / "base" / "5_route_drc.rpt"
        if r.is_file():
            d["drc_rpt"] = str(r)
    if kit:
        for n in ("pins.json",):
            if (kit / n).is_file():
                d["pins"] = str(kit / n)
        if (kit / "sdc_lint.json").is_file():
            d["sdc_lint_ctx"] = str(kit / "sdc_lint.json")
    return d


def macro_libs(kit, corner):
    """(host paths of the corner's macro liberty files, missing corner list) from shared or corner-scoped KIT/config.mk libraries."""
    if not kit or not (Path(kit) / "config.mk").is_file():
        return [], []
    txt = (Path(kit) / "config.mk").read_text(errors="replace").replace("\\\n", " ")
    libs, missing = [], []
    field = {"tt": "TC_LIB_FILES", "ff": "BC_LIB_FILES", "ss": "WC_LIB_FILES"}[corner]
    for m in re.finditer(r"^[ \t]*(?:export[ \t]+)?(ADDITIONAL_LIBS|TC_LIB_FILES|BC_LIB_FILES|WC_LIB_FILES)[ \t]*[:+?]?=[ \t]*(.*)$", txt, re.M):
        if m.group(1) not in ("ADDITIONAL_LIBS", field):
            continue
        scoped = m.group(1) == field
        for w in m.group(2).split():
            if re.fullmatch(r"\$\((TC|BC|WC)_NLDM_LIB_FILES\)", w):
                continue  # standard cells are loaded independently for this corner
            w = w.replace("$(KIT)", "/work").replace("${KIT}", "/work")
            if not w.startswith("/work/"):
                missing.append(f"{w} (not under /work)")
                continue
            p = Path(kit) / w[len("/work/"):]
            cand = None
            mm = re.match(r"^(.*)_(ss|tt|ff|typ)(\.lib(?:\.gz)?)$", p.name)
            if mm:
                for suf in ([corner] if corner != "tt" else ["tt", "typ"]):
                    q = p.with_name(f"{mm.group(1)}_{suf}{mm.group(3)}")
                    if q.is_file():
                        cand = q
                        break
            elif p.is_file() and (corner == "tt" or scoped):
                cand = p
            if cand is None:
                missing.append(f"{p.name} ({corner})")
            else:
                libs.append(str(cand))
    return list(dict.fromkeys(libs)), missing


# ---- the OpenSTA session (one corner) -----------------------------------------------------------------------------
def _clock_family_tcl():
    for p in (REPO / "physical/common_flow/clock_family.tcl", HERE / "clock_family.tcl"):   # repo, or a kit copy
        if p.is_file():
            return p.read_text()
    return ""



# Opt-in corner-specific core clock reference.  Preserve the golden-SDC timing
# above and change the ONE shared virtual clock, hence both input and output
# budgets coherently.  Never change clock period, uncertainty, or IO delays.
FF_VCLK_TCL = r"""
@CLOCK_FAMILY@
set so_ff_regs {}
foreach p [all_registers -clock_pins] { dict set so_ff_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
set so_ff_data {}
set so_ff_async {}
foreach p [all_registers -async_pins] { dict set so_ff_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] {
  set n [get_full_name $p]
  if {![dict exists $so_ff_async $n]} { dict set so_ff_data $n 1 }
}
set so_ff_bnd {}
if {[llength $so_din]} {
  foreach p [get_fanout -from $so_din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $so_ff_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $so_ff_regs $i]} { dict set so_ff_bnd $i 1 }
  }
}
if {[llength [all_outputs]]} {
  foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $so_ff_regs $i]} { dict set so_ff_bnd $i 1 }
  }
}
set so_ff_sum 0.0
set so_ff_n 0
set so_ff_bad 0
set so_ff_clocks {}
if {[llength [info commands ot_cf_refresh]]} { catch {ot_cf_refresh} }
dict for {i unused} $so_ff_bnd {
  set p [dict get $so_ff_regs $i]
  set cl [get_property $p clocks]
  set a ""
  if {[llength $cl] == 1} {
    dict set so_ff_clocks [get_full_name [lindex $cl 0]] 1
    if {[llength [info commands ot_cf_wire]]} { catch {set a [ot_cf_wire $p [lindex $cl 0]]} }
    if {$a eq ""} { catch {set a [get_property $p arrival_max_rise]} }
  }
  if {![string is double -strict $a] || [regexp -nocase {inf|nan} $a]} { incr so_ff_bad; continue }
  set so_ff_sum [expr {$so_ff_sum + $a}]
  incr so_ff_n
}
if {[llength $so_vclk] == 1 && $so_ff_n > 0 && $so_ff_bad == 0 && [dict size $so_ff_clocks] == 1} {
  set so_ff_mean [expr {$so_ff_sum / $so_ff_n}]
  set_clock_latency -source $so_ff_mean [lindex $so_vclk 0]
  so FF_VCLK applied mode pin_flop_mean clock [get_full_name [lindex $so_vclk 0]] latency_ps [format %.6f $so_ff_mean] samples $so_ff_n missing $so_ff_bad clocks [dict size $so_ff_clocks]
} else {
  set so_reference_ok 0
  so FF_VCLK unavailable mode pin_flop_mean vclks [llength $so_vclk] samples $so_ff_n missing $so_ff_bad
}
"""

# FLOW-FIX 10-25 'bound-ff' (hard-core latency contract kits, ROOT-MERGE2: no rebind inside a core): the FF session
# times IO against the kit's DECLARED FF insertion (sdc_lint ctx insertion_ff_ps, the same value the in-flow FF hold
# repair bound), never silently against the single SDC (TT) vclk latency.
FF_BOUND_TCL = r"""
if {[llength $so_vclk] == 1} {
  set_clock_latency -source @FF_BOUND@ [lindex $so_vclk 0]
  so FF_VCLK applied mode bound_ff clock [get_full_name [lindex $so_vclk 0]] latency_ps @FF_BOUND@
} else {
  set so_reference_ok 0
  so FF_VCLK unavailable mode bound_ff vclks [llength $so_vclk]
}
"""

EXACT_TIMING_LIBRARIES_TCL = r"""# Resolve the exact libraries selected by this kit's ORFS make configuration.
# No directory glob or installed-version fallback is permitted.
proc ot_lib_json_string {value} {
  return "\"[string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t] $value]\""
}
proc ot_lib_validate {corner files} {
  if {$corner ni {TT FF SS}} {error "OT_TIMING_LIBS: unsupported corner $corner"}
  if {![llength $files]} {error "OT_TIMING_LIBS: empty exact library list"}
  set seen {}; set groups {}; set present {}
  foreach f $files {
    if {[file pathtype $f] ne "absolute"} {error "OT_TIMING_LIBS: relative library $f"}
    if {[regexp {[*?\[\]$]} $f] || ![file isfile $f]} {error "OT_TIMING_LIBS: missing or unresolved library $f"}
    set path [file normalize $f]
    if {[dict exists $seen $path]} {error "OT_TIMING_LIBS: duplicate library $f"}
    dict set seen $path 1
    if {[regexp {^asap7sc7p5t_([^_]+)_(RVT|LVT|SLVT)_(TT|FF|SS)_nldm_} [file tail $f] -> group vt actual]} {
      if {$actual ne $corner} {error "OT_TIMING_LIBS: wrong corner $f"}
      set key $group/$vt
      if {[dict exists $groups $key]} {error "OT_TIMING_LIBS: ambiguous installed versions for $key"}
      dict set groups $key $path
      dict set present $group 1
    } elseif {[regexp -nocase {_(tt|ff|ss|typ)\.lib(?:\.gz)?$} [file tail $f] -> actual]} {
      set actual [string toupper $actual]
      if {$actual eq "TYP"} {set actual TT}
      if {$actual ne $corner} {error "OT_TIMING_LIBS: wrong macro corner $f"}
    }
  }
  foreach group {AO INVBUF OA SEQ SIMPLE} {
    if {![dict exists $present $group]} {error "OT_TIMING_LIBS: missing standard-cell group $group"}
  }
  return $files
}
proc ot_lib_resolve {corner {config /work/config.mk}} {
  if {![file isfile $config]} {error "OT_TIMING_LIBS: missing exact ORFS config $config"}
  set field [dict get {TT TC_LIB_FILES FF BC_LIB_FILES SS WC_LIB_FILES} $corner]
  set output [exec bash -c {source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 || exit; exec make --no-print-directory -s -C /OpenROAD-flow-scripts/flow "DESIGN_CONFIG=$1" "print-$2"} otlibs $config $field]
  set records {}
  foreach line [split $output \n] {
    if {[regexp "^${field}\\s*\[:=\]\\s*(.*)$" $line -> value]} {lappend records $value}
  }
  if {[llength $records] != 1} {error "OT_TIMING_LIBS: missing or ambiguous make $field result"}
  set files [regexp -all -inline {\S+} [lindex $records 0]]
  return [ot_lib_validate $corner $files]
}
proc ot_lib_load {corner receipt {config /work/config.mk}} {
  if {[file exists $receipt]} {file rename $receipt ${receipt}.previous.[clock clicks]}
  set files [ot_lib_resolve $corner $config]
  set rows {}
  foreach f $files {
    set digest [lindex [exec sha256sum -- $f] 0]
    lappend rows "{\"path\":[ot_lib_json_string $f],\"sha256\":[ot_lib_json_string $digest]}"
  }
  set digest [lindex [exec sha256sum -- $config] 0]
  foreach f $files {read_liberty $f}
  set fp [open $receipt w]
  puts $fp "{\"status\":\"LOADED\",\"corner\":[ot_lib_json_string $corner],\"source\":\"ORFS make print corner LIB_FILES\",\"config\":[ot_lib_json_string $config],\"config_sha256\":[ot_lib_json_string $digest],\"libraries\":\[[join $rows ,]\]}"
  close $fp
  puts "OT_TIMING_LIBS $corner exact_count [llength $files] receipt $receipt"
  return $files
}
"""

SESSION_TCL = r"""
proc so {k args} { puts "SO $k [join $args { }]" }
proc so_ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.2f [sta::time_sta_ui $t]] }
@TIMING_LIBRARIES@
ot_lib_load @C@ /out/libraries.json
read_db /base/@ODB@
@PARASITICS@
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
so CORNER @C@
so PARASITICS @PARSRC@
so DESIGN [current_design]
so CELLS [llength [get_cells *]]
# ---- ports (for sdc_lint context) and IO virtual clock ----
set so_ck_ports {}
foreach c [all_clocks] { foreach s [get_property $c sources] { if {[llength [get_ports -quiet [get_full_name $s]]]} { lappend so_ck_ports [get_full_name $s] } } }
set so_ck_ports [lsort -unique $so_ck_ports]
so CLOCK_PORTS {*}$so_ck_ports
set so_din {}
foreach p [all_inputs] { if {[get_full_name $p] ni $so_ck_ports} { lappend so_din $p } }
so INPUTS {*}[lsort -unique [lmap p $so_din {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
so OUTPUTS {*}[lsort -unique [lmap p [all_outputs] {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
set so_vclk {}
foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend so_vclk $c } }
so CLOCKS {*}[lmap c [all_clocks] {get_full_name $c}]
so VCLKS {*}[lmap c $so_vclk {get_full_name $c}]
foreach c [all_clocks] { so PERIOD [get_full_name $c] [get_property $c period] }
# ---- timing with the block's own SDC ----
proc so_timing {tag} {
  so ${tag}_WNS_MAX [so_ps [sta::worst_slack_cmd max]]
  so ${tag}_WNS_MIN [so_ps [sta::worst_slack_cmd min]]
  so ${tag}_TNS_MAX [so_ps [sta::total_negative_slack_cmd max]]
  so ${tag}_TNS_MIN [so_ps [sta::total_negative_slack_cmd min]]
  so ${tag}_NVIOL_MAX [sta::endpoint_violation_count max]
  so ${tag}_NVIOL_MIN [sta::endpoint_violation_count min]
}
so_timing SDC
puts "SO_PATH_BEGIN SDC_MAX"
report_checks -path_delay max -format full_clock_expanded -digits 2 -fields {slew cap fanout}
puts "SO_PATH_END"
# ---- standard boundary-hold overlay (4b7b2b3e64 kit standard) ----
set so_reference_ok 1
@FF_VCLK@
if {[llength $so_vclk] == 1 && $so_reference_ok} {
  if {[llength $so_din]} { set_input_delay -min @IN_MIN@ -clock [lindex $so_vclk 0] $so_din }
  if {[llength [all_outputs]]} { set_output_delay -min @OUT_MIN@ -clock [lindex $so_vclk 0] [all_outputs] }
@IN_MIN_PORTS@
  so OVERLAY applied [get_full_name [lindex $so_vclk 0]] in_min @IN_MIN_LOG@ out_min @OUT_MIN@
} else {
  so OVERLAY skipped vclks [llength $so_vclk]
}
so_timing STD
puts "SO_PATH_BEGIN STD_MIN"
report_checks -path_delay min -format full_clock_expanded -digits 2
puts "SO_PATH_END"
# ---- DRV ----
so SLEW_VIOL [sta::max_slew_violation_count]
so CAP_VIOL [sta::max_capacitance_violation_count]
set so_fo_max 0; set so_fo_n 0; set so_fo_worst ""
foreach n [get_nets -hierarchical *] {
  set k [llength [get_pins -quiet -of_objects $n -filter "direction==input"]]
  if {$k > $so_fo_max} { set so_fo_max $k; set so_fo_worst [get_full_name $n] }
  if {$k > @FANOUT_MAX@} { incr so_fo_n }
}
so FANOUT_MAX $so_fo_max $so_fo_worst
so FANOUT_VIOL $so_fo_n
puts "SO_PATH_BEGIN DRV"
report_check_types -max_slew -max_capacitance -violators -max_count 10
puts "SO_PATH_END"
# ---- constraint coverage ----
puts "SO_PATH_BEGIN CHECK_SETUP"
check_setup -verbose -unconstrained_endpoints -no_clock -loops -generated_clocks -multiple_clock
puts "SO_PATH_END"
# ---- OCV sensitivity (information only) ----
set_timing_derate -late 1.05
set_timing_derate -early 0.95
so OCV5_WNS_MAX [so_ps [sta::worst_slack_cmd max]]
so OCV5_WNS_MIN [so_ps [sta::worst_slack_cmd min]]
unset_timing_derate
# ---- related flop-pair skew with CPPR (owner gate, BRIEFING decision 5) ----
# Measured on the golden SDC exactly as loaded (source latencies, propagated clocks, derate removed), BEFORE the
# insertion diagnostic below zeroes clock source latency; only the clock uncertainty is zeroed (clk_skew must not
# carry it) and nothing after this block reads slack.
set ::ot_ps_lib_only 1
@PAIR_SKEW@
unset ::ot_ps_lib_only
ot_ps_zero_unc
set so_t0 [clock seconds]
set so_pm [ot_ps_measure @PAIR_CREDIT_MAX@]
ot_ps_write $so_pm /out/pair_skew.tsv @C@
so PAIR_COUNTS regs [dict get $so_pm regs] no_clock_arrival [dict get $so_pm no_clock_arrival] data_pins [dict get $so_pm data_pins] pairs [dict get $so_pm pairs] inter_clock [dict get $so_pm inter_clock]
foreach dly {max min} {
  set m [dict get $so_pm $dly]
  so PAIR_$dly {*}[concat {*}[lmap k {n worst bounded signed launch capture crpr p99_raw searched nopath verify} {list $k [dict get $m $k]}]]
}
so PAIR_METHOD [dict get $so_pm method]
so PAIR_SECONDS [expr {[clock seconds] - $so_t0}]
unset so_pm
so PAIR_DONE 1
# ---- clock: active-edge arrival at register clock pins, pin flops ----
@CLOCK_FAMILY@
set so_regs {}
foreach p [all_registers -clock_pins] { dict set so_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
set so_bnd {}
dict for {inst pin} [ot_cf_pinregs] { dict set so_bnd $inst 1 }
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
set so_ck_err 0
set so_cf [llength [info commands ot_cf_wire]]
if {$so_cf} { catch {ot_cf_refresh} }
dict for {i p} $so_regs {
  set cl [get_property $p clocks]
  if {[llength $cl] != 1} { incr so_ck_err; continue }
  set a ""
  if {$so_cf} { catch {set a [ot_cf_wire $p [lindex $cl 0]]} }
  if {$a eq ""} {
    # get_property returns display units already (PropertyValue timeUnit);
    # converting again multiplies ASAP7 ps arrivals by 1e12.
    catch {set a [get_property $p arrival_max_rise]}
  }
  if {$a eq "" || ![string is double -strict $a]} { incr so_ck_err; continue }
  puts "SO_CK [expr {[dict exists $so_bnd $i] ? 1 : 0}] [format %.2f $a] [get_full_name [lindex $cl 0]]"
}
so CK_ERRORS $so_ck_err
so DONE 1
exit
"""


def session_tcl(corner, mlibs_ctr, spef, ins_tol=INSERTION_TOL_PS, fanout_max=FANOUT_MAX, odb="6_final.odb",
                ff_vclk="sdc", ff_bound_ps=None, hold_in_min=None, hold_out_min=None, hold_in_min_ports=None):
    """mlibs_ctr is retained for API compatibility; exact make-selected libraries include all macro views.

    hold_in_min / hold_out_min: the kit's seam hold contract (sdc_lint.json hold_in_min_ps / hold_out_min_ps,
    CLOCK-RESET IO-HOLD 10-25); None = legacy overlay (min input -ins_tol, min output 0).  hold_in_min_ports
    {input port: ps}: IO-HOLD option A per-port min input delays (sdc_lint.json hold_in_min_ports_ps) applied after
    the uniform one; None / {} = no per-port lines (session byte-identical)."""
    hin = -float(ins_tol) if hold_in_min is None else float(hold_in_min)
    hout = 0.0 if hold_out_min is None else float(hold_out_min)
    if hout > 0:
        raise ValueError(f"hold overlay: min output delay {hout:g} > 0 waives the sender hold check")
    if spef:
        par, src = "read_spef /base/6_final.spef", "spef"
    else:
        par, src = (f"source {PLAT}/setRC.tcl\nextract_parasitics -ext_model_file {PLAT}/rcx_patterns.rules\n"
                    "write_spef /out/rcx.spef\nread_spef /out/rcx.spef"), "rcx"
    if ff_vclk not in VCLK_MODES:
        raise ValueError("unsupported FF virtual-clock reference")
    # FLOW 10-25 'rebind' (ruling 9.7 / 5e): EVERY sign-off corner times its IO paths against that corner's routed
    # RCX pin-register mean; the clock check bounds it against the kit's per-corner bound insertion
    on = (corner == "ff" and ff_vclk == "pin-flop-mean") or (corner in ("tt", "ff") and ff_vclk == "rebind")
    if corner == "ff" and ff_vclk == "bound-ff":
        if ff_bound_ps is None:
            raise ValueError("bound-ff needs the declared FF insertion (ff_bound_ps)")
        t = SESSION_TCL.replace("@FF_VCLK@", FF_BOUND_TCL.replace("@FF_BOUND@", f"{float(ff_bound_ps):.6f}"))
    else:
        t = SESSION_TCL.replace("@FF_VCLK@", FF_VCLK_TCL if on else "")
    for k, v in (("@ODB@", odb), ("@PLAT@", PLAT), ("@C@", corner.upper()), ("@PARASITICS@", par), ("@PARSRC@", src),
                 ("@TIMING_LIBRARIES@", EXACT_TIMING_LIBRARIES_TCL),
                 ("@INS_TOL@", f"{ins_tol:g}"), ("@IN_MIN@", f"[expr {{-{ins_tol:g}}}]" if hold_in_min is None else f"{hin:g}"),
                 ("@IN_MIN_LOG@", f"{hin:g}"), ("@OUT_MIN@", f"{hout:g}"),
                 ("@IN_MIN_PORTS@\n", "".join(
                     f"  set_input_delay -min {v:g} -clock [lindex $so_vclk 0] [get_ports {{{' '.join(p + '[*]' for p in ps)}}}]\n"
                     for v, ps in _group_ports(hold_in_min_ports))),
                 ("@FANOUT_MAX@", str(int(fanout_max))),
                 ("@CLOCK_FAMILY@", _clock_family_tcl()),
                 ("@PAIR_SKEW@", (HERE / "pair_skew.tcl").read_text()),
                 ("@PAIR_CREDIT_MAX@", str(int(PAIR_CREDIT_MAX)))):
        t = t.replace(k, v)
    return t


def _group_ports(m):
    """{port: ps} -> [(ps, [ports])] sorted (one overlay command per distinct value)."""
    g = {}
    for p, v in (m or {}).items():
        g.setdefault(float(v), []).append(p)
    return sorted((v, sorted(ps)) for v, ps in g.items())


def parse_session(text):
    """SO lines -> dict; SO_CK -> clock arrays; SO_PATH blocks -> text."""
    r = dict(kv={}, ck=[], blocks={})
    blk, buf = None, []
    for ln in text.splitlines():
        if ln.startswith("SO_PATH_BEGIN "):
            blk, buf = ln.split(None, 1)[1].strip(), []
            continue
        if ln.startswith("SO_PATH_END"):
            if blk:
                r["blocks"][blk] = "\n".join(buf)[-20000:]
            blk = None
            continue
        if blk is not None:
            buf.append(ln)
            continue
        if ln.startswith("SO_CK "):
            f = ln.split()
            try:
                r["ck"].append((int(f[1]), float(f[2]), f[3] if len(f) > 3 else ""))
            except (ValueError, IndexError):
                pass
            continue
        if ln.startswith("SO "):
            f = ln.split(None, 2)
            if len(f) >= 2:
                k = f[1]
                v = f[2] if len(f) > 2 else ""
                if k == "PERIOD":
                    c, p = v.split()
                    r["kv"].setdefault("PERIOD", {})[c] = _f(p)
                else:
                    r["kv"][k] = v
    return r


def _f(x):
    try:
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def stats(v):
    if not v:
        return None
    return dict(n=len(v), min=round(min(v), 2), mean=round(sum(v) / len(v), 2), max=round(max(v), 2),
                spread=round(max(v) - min(v), 2))


def check_setup_counts(text):
    """counts from check_setup output."""
    c = dict(unconstrained=0, unclocked=0, loops=0, multiple_clock=0, generated=0)
    for ln in text.splitlines():
        m = re.search(r"There (?:are|is) (\d+) unconstrained endpoints?", ln)
        if m:
            c["unconstrained"] = int(m.group(1))
        m = re.search(r"There (?:are|is) (\d+) register/latch pins? with no clock", ln)
        if m:
            c["unclocked"] = int(m.group(1))
        m = re.search(r"There (?:are|is) (\d+) combinational loops?", ln)
        if m:
            c["loops"] = int(m.group(1))
        m = re.search(r"There (?:are|is) (\d+) pins? with multiple clocks", ln)
        if m:
            c["multiple_clock"] = int(m.group(1))
        m = re.search(r"There (?:are|is) (\d+) generated clocks? that (?:are|is) not connected", ln)
        if m:
            c["generated"] = int(m.group(1))
    return c


def corner_result(parsed):
    kv = parsed["kv"]
    allck = [a for _, a, _ in parsed["ck"]]
    bnd = [a for b, a, _ in parsed["ck"] if b]
    out = dict(done=kv.get("DONE") == "1", design=kv.get("DESIGN"), cells=_f(kv.get("CELLS")),
               parasitics=kv.get("PARASITICS"), clocks=(kv.get("CLOCKS") or "").split(),
               vclks=(kv.get("VCLKS") or "").split(), periods=kv.get("PERIOD", {}),
               clock_ports=(kv.get("CLOCK_PORTS") or "").split(), inputs=(kv.get("INPUTS") or "").split(),
               outputs=(kv.get("OUTPUTS") or "").split(), overlay=kv.get("OVERLAY"),
               ff_vclk_reference=kv.get("FF_VCLK"))
    for tag in ("SDC", "STD"):
        for k in ("WNS_MAX", "WNS_MIN", "TNS_MAX", "TNS_MIN", "NVIOL_MAX", "NVIOL_MIN"):
            out[f"{tag.lower()}_{k.lower()}"] = _f(kv.get(f"{tag}_{k}"))
    out["slew_viol"] = _f(kv.get("SLEW_VIOL"))
    out["cap_viol"] = _f(kv.get("CAP_VIOL"))
    fo = (kv.get("FANOUT_MAX") or "").split()
    out["fanout_max"] = _f(fo[0]) if fo else None
    out["fanout_worst_net"] = fo[1] if len(fo) > 1 else None
    out["fanout_viol"] = _f(kv.get("FANOUT_VIOL"))
    out["check_setup"] = check_setup_counts(parsed["blocks"].get("CHECK_SETUP", ""))
    out["ck_errors"] = _f(kv.get("CK_ERRORS"))
    out["insertion_all"] = stats(allck)
    out["insertion_pinflops"] = stats(bnd)
    out["pair_skew"] = pair_skew_result(kv)
    out["ocv5_wns_max"] = _f(kv.get("OCV5_WNS_MAX"))
    out["ocv5_wns_min"] = _f(kv.get("OCV5_WNS_MIN"))
    return out


def _kvlist(text):
    """'k1 v1 k2 v2 ...' -> dict (values as text)"""
    f = (text or "").split()
    return dict(zip(f[0::2], f[1::2]))


def pair_skew_result(kv):
    """the SO PAIR_* lines of a corner session (pair_skew.tcl ot_ps_measure): per check (max = setup, min = hold) the
    EXHAUSTIVE related-pair count, the worst CPPR-credited damage (setup: launch late vs capture early; hold: capture
    late vs launch early; = the die_sta.py pair skew), whether it is exact or a bound, and the uncredited p99."""
    checks = {}
    for dly in ("max", "min"):
        d = _kvlist(kv.get(f"PAIR_{dly}"))
        if not d:
            continue
        checks[dly] = dict(n=_f(d.get("n")), worst_abs_ps=_f(d.get("worst")), bounded=d.get("bounded") == "1",
                           worst_signed_ps=_f(d.get("signed")), worst_launch=d.get("launch"),
                           worst_capture=d.get("capture"), worst_crpr_ps=_f(d.get("crpr")),
                           p99_raw_ps=_f(d.get("p99_raw")), searched=_f(d.get("searched")),
                           nopath=_f(d.get("nopath")), verify_ps=_f(d.get("verify")))
    cnt = {k: _f(v) for k, v in _kvlist(kv.get("PAIR_COUNTS")).items()}
    return dict(done=kv.get("PAIR_DONE") == "1", checks=checks, counts=cnt, method=kv.get("PAIR_METHOD"), seconds=_f(kv.get("PAIR_SECONDS")),
                measurement="every same-clock register pair with a timing fan-in relation (exhaustive); worst "
                            "damage CPPR-credited from the pair's own path end (exact unless bounded); p99 uncredited",
                tsv="pair_skew.tsv")


def run_corner(corner, disc, out, image=IMAGE, docker="sudo docker", dry=False, ff_vclk="sdc"):
    od = Path(out) / corner
    od.mkdir(parents=True, exist_ok=True)
    mlibs, mmiss = macro_libs(disc["kit"], corner)
    mounts = [("base", disc["base"]), ("sdc", str(od / "sdcdir")), ("out", str(od))]
    (od / "sdcdir").mkdir(exist_ok=True)
    (od / "sdcdir" / "golden.sdc").write_text(Path(disc["sdc"]).read_text())
    libconfig = Path(disc["library_config"]) if disc.get("library_config") else (Path(disc["kit"]) / "config.mk" if disc.get("kit") else None)
    if libconfig is None or not libconfig.is_file():
        raise ValueError("signoff: exact corner libraries require --kit/config.mk or explicit --library-config")
    mounts.append(("work", disc.get("kit") or str(libconfig.parent)))
    mounts.append(("work/config.mk", str(libconfig)))
    ml_ctr = []
    lctx = json.loads(Path(disc["sdc_lint_ctx"]).read_text()) if disc.get("sdc_lint_ctx") else {}
    (od / "session.tcl").write_text(session_tcl(corner, ml_ctr, disc["spef"], odb=Path(disc["odb"]).name, ff_vclk=ff_vclk,
                                                ff_bound_ps=disc.get("ff_bound_ps"),
                                                hold_in_min=lctx.get("hold_in_min_ps"),
                                                hold_out_min=lctx.get("hold_out_min_ps"),
                                                hold_in_min_ports=lctx.get("hold_in_min_ports_ps")))
    vol = " ".join(f"-v {shlex.quote(h)}:/{c}" + ("" if c == "out" or c == "sdc" else ":ro") for c, h in mounts)
    cmd = (f"{docker} run --rm --name so_{os.getpid()}_{corner}_{abs(hash(disc['base'])) % 100000} {vol} {image} "
           f"{OPENROAD} -no_init -exit /out/session.tcl")
    (od / "cmd.sh").write_text(cmd + "\n")
    if dry:
        return dict(corner=corner, cmd=cmd, macro_libs=mlibs, macro_missing=mmiss)
    with open(od / "sta.log", "w") as lf:
        rc = subprocess.call(cmd, shell=True, stdout=lf, stderr=subprocess.STDOUT)
    text = (od / "sta.log").read_text(errors="replace")
    res = corner_result(parse_session(text))
    res.update(corner=corner, rc=rc, macro_libs=mlibs, macro_missing=mmiss,
               errors=re.findall(r"\[ERROR[^\n]*", text)[:5])
    (od / "corner.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


# ---- record checks -------------------------------------------------------------------------------------------------
def route_counts(disc):
    """DRC / antenna counts from the ORFS route metrics, else the gate record, else the DRC report."""
    r = dict(drc=None, antenna_nets=None, drc_source=None, antenna_source=None)
    mp = disc["metrics"].get("5_2_route.json")
    if mp:
        m = json.loads(Path(mp).read_text())
        if "detailedroute__route__drc_errors" in m:
            r["drc"], r["drc_source"] = int(m["detailedroute__route__drc_errors"]), "5_2_route.json"
        if "detailedroute__antenna__violating__nets" in m:
            r["antenna_nets"] = int(m["detailedroute__antenna__violating__nets"])
            r["antenna_source"] = "5_2_route.json"
    if r["drc"] is None and disc.get("record"):
        rec = json.loads(Path(disc["record"]).read_text())
        for k in ("drc", "drc_errors", "route_drc"):
            if isinstance(rec.get(k), (int, float)):
                r["drc"], r["drc_source"] = int(rec[k]), f"record:{k}"
        for k in ("antenna", "antenna_nets", "antenna_violating_nets"):
            if isinstance(rec.get(k), (int, float)):
                r["antenna_nets"], r["antenna_source"] = int(rec[k]), f"record:{k}"
    if r["drc"] is None and disc.get("drc_rpt"):
        txt = Path(disc["drc_rpt"]).read_text(errors="replace")
        r["drc"], r["drc_source"] = len(re.findall(r"violation type", txt)), "5_route_drc.rpt"
    return r


def run_sdc_lint(disc, ports):
    import sdc_lint
    text = Path(disc["sdc"]).read_text()
    if disc.get("sdc_lint_ctx"):
        ctx = json.loads(Path(disc["sdc_lint_ctx"]).read_text())
        mode = "kit sdc_lint.json"
    else:
        ins = INSERTION_PS
        m = re.search(r"set_clock_latency\s+-source\s+([0-9.]+)", text)
        if m:
            ins = float(m.group(1))
        ctx = dict(period_ps=PERIOD_PS, insertion_ps=ins, insertion_tol_ps=INSERTION_TOL_PS,
                   clock_ports=ports["clock_ports"], inputs=ports["inputs"], outputs=ports["outputs"],
                   unc_setup_ps=UNC_SETUP_PS, unc_hold_ps=UNC_HOLD_PS, time_unit_ps=1.0)
        mode = "derived (plan period 833, insertion from SDC vclk latency, tol 40, 60/25)"
    try:
        err = sdc_lint.lint(text, **ctx)
    except Exception as e:                    # parser limits are a FAIL with the reason, never a pass
        err = [f"sdc_lint could not evaluate the SDC: {e}"]
    return dict(verdict="PASS" if not err else "FAIL", mode=mode, errors=err[:40], n_errors=len(err),
                sdc=disc["sdc"], sdc_source=disc["sdc_source"])


def boundary_controls(disc):
    """Read a generated core's typed control contract; never exempt data pins."""
    if not disc.get("kit"):
        return [], None
    manifest = Path(disc["kit"]) / "boundary_guard_context.json"
    if not manifest.is_file():
        return [], None
    ctx = json.loads(manifest.read_text())
    if ctx.get("schema") != "opentallas.core_boundary_guard_context.v1":
        raise ValueError("unsupported boundary guard context schema")
    if ctx.get("data_pin_exemptions") != []:
        raise ValueError("boundary context cannot exempt data pins")
    source = Path(ctx["source_core_json"])
    if not source.is_absolute():
        source = manifest.parent / source
    roles = json.loads(source.read_text()).get("boundary_role")
    if not isinstance(roles, dict):
        raise ValueError("source core metadata lacks typed boundary_role map")
    controls = []
    for field, role in (("clock_ports", "clk"), ("unused_clock_ports", "clk_unused"), ("reset_ports", "reset")):
        ports = ctx.get(field, [])
        if not isinstance(ports, list) or any(not isinstance(x, str) or not x or "\n" in x for x in ports):
            raise ValueError(f"invalid {field} in boundary context")
        for port in ports:
            if port in controls or roles.get(port) != role:
                raise ValueError(f"boundary role mismatch or duplicate: {port} expected {role}")
            controls.append(port)
    return controls, dict(manifest=str(manifest), source_core_json=str(source), controls=controls)


def hard_core_latency_contract(disc):
    """the kit's typed hard-core clock contract (boundary_guard_context.json -> core.json clock_contract), or None.
    Only kind 'hard_core_latency' is recognised: the core publishes its measured insertion instead of meeting the
    partition-tap target (COORD 10-24)."""
    if not disc.get("kit"):
        return None
    manifest = Path(disc["kit"]) / "boundary_guard_context.json"
    if not manifest.is_file():
        return None
    ctx = json.loads(manifest.read_text())
    source = Path(ctx.get("source_core_json", ""))
    if not source.is_absolute():
        source = manifest.parent / source
    if not source.is_file():
        return None
    cc = json.loads(source.read_text()).get("clock_contract")
    if not isinstance(cc, dict) or cc.get("kind") != "hard_core_latency":
        return None
    return cc


def run_face_guard(disc, clock_ports=()):
    import face_guard
    if not disc.get("synth"):
        return dict(verdict="NOT RUN", reason="no synthesized netlist (1_synth.v / 1_2_yosys.v) in the routed base")
    pins = json.loads(Path(disc["pins"]).read_text()) if disc.get("pins") else None
    if isinstance(pins, dict):
        pins = pins.get("pins")
    if pins is not None and not (isinstance(pins, list) and pins and isinstance(pins[0], dict) and "bus" in pins[0]):
        pins = None
    try:
        typed_controls, context = boundary_controls(disc)
    except Exception as e:
        return dict(verdict="FAIL", reason=f"invalid boundary control context: {e}", fail_counts={"context": 1})
    skip = sorted(set(clock_ports) | set(typed_controls) | {"arst_n", "rst_n"})
    # Keep the guard's canonical clock/reset contract (including registered wavefront rst_o_<k>
    # controls). Supplying the native-clock override must not turn reset-tree fanout into a data-face failure.
    skip_re = r"(?:" + face_guard.SKIP_RE + r")|^(?:" + "|".join(re.escape(x) for x in skip) + r")$"
    if pins is not None:                      # the clock / reset pins are not face registers
        pins = [x for x in pins if not re.match(skip_re, str(x.get("bus")))]
    ft_file = Path(disc["kit"]) / "ft_stations.txt" if disc.get("kit") else (
        Path(disc["pins"]).with_name("ft_stations.txt") if disc.get("pins") else None)
    try:
        ft1 = face_guard.read_ft1(ft_file) if ft_file and ft_file.is_file() else set()
        # OWNER 10-25 option B: declared ID straps (kit straps.json / core.json id_strap) need no pin register
        sl = face_guard.kit_strap_list(disc["kit"]) if disc.get("kit") else []
        r = face_guard.guard(Path(disc["synth"]).read_text(errors="replace"), pins=pins, skip_re=skip_re, ft1=ft1,
                             straps=sl)
    except Exception as e:
        return dict(verdict="NOT RUN", reason=f"face_guard error: {e}", netlist=disc["synth"])
    return dict(verdict=r["verdict"], top=r.get("top"), checked=r.get("checked"), ok=r.get("ok"),
                fail_counts=r.get("fail_counts"), fails={k: v[:5] for k, v in (r.get("fails") or {}).items()},
                netlist=disc["synth"], pins=disc.get("pins"), boundary_context=context,
                one_station_ft_slots=sorted(ft1))


# ---- verdict -------------------------------------------------------------------------------------------------------
FF_REF_TOL_PS = 10.0   # COORD 10-25 (GEOM-REVIEW-3 HBM argmax la1/s2f2): FF IO latency == TT vs measured FF mean


def ff_reference_problem(rec, cff, requested):
    """COORD 10-25: FF hold must be timed against a per-corner FF insertion reference, never silently against the
    kit SDC's single (TT) IO vclk latency.  HBM argmax la1/s2f2 signed FF hold vs 250 ps while its routed FF
    pin-register mean was 198.4 ps (-27.8 reported, ~+24 real).  -> 'FAIL_SIGNOFF ff_ref_missing: ...' or None.
      * ff_vclk 'sdc' (no rebind / pin-flop-mean reference) and no per-corner FF bound -> FAIL;
      * a FF bound equal to the TT value while the measured FF pin-register mean differs from it by > 10 ps -> FAIL."""
    pol = rec.get("policy", {})
    b = pol.get("insertion_bound") or {}
    ffm = (cff.get("insertion_pinflops") or {}).get("mean")
    if requested == "bound-ff":
        if pol.get("ff_vclk_bound_ps") is None:
            return "FAIL_SIGNOFF ff_ref_missing: bound-ff requested without a declared FF insertion"
        return None
    if requested == "sdc" and b.get("ff") is None:
        return ("FAIL_SIGNOFF ff_ref_missing: no per-corner FF insertion reference (ff_vclk sdc: FF hold timed against "
                "the single SDC/TT IO vclk latency" + (f"; measured FF pin-register mean {ffm:.1f} ps" if ffm is not None
                                                       else "") + "); regenerate the kit with the per-corner binding")
    if b.get("ff") is not None and b.get("tt") is not None and abs(float(b["ff"]) - float(b["tt"])) < 0.5 \
            and ffm is not None and abs(ffm - float(b["ff"])) > FF_REF_TOL_PS:
        return (f"FAIL_SIGNOFF ff_ref_missing: FF IO latency {float(b['ff']):g} ps equals the TT value while the measured "
                f"FF pin-register mean is {ffm:.1f} ps (> {FF_REF_TOL_PS:g} ps apart)")
    return None


def evaluate(rec, insertion_target=None):
    """fills rec['checks'] and rec['verdict'] / rec['reasons'] from rec['corners'] + record checks."""
    C = rec.get("corners", {})
    ch = {}

    def ok_corner(c):
        x = C.get(c)
        return x is not None and x.get("done")

    def put(name, verdict, **kw):
        ch[name] = dict(verdict=verdict, **kw)

    # setup TT (the sign-off corner, AGENTS.md 2026-10-24)
    requested = rec.get("policy", {}).get("ff_vclk", "sdc")
    if requested == "rebind" and ok_corner("tt") and C["tt"].get("std_wns_max") is not None:
        w = C["tt"]["std_wns_max"]
        ref = C["tt"].get("ff_vclk_reference") or ""
        v = ("PASS" if w >= 0 else "FAIL") if ref.startswith("applied mode pin_flop_mean ") else "NOT RUN"
        put("setup_tt", v, wns_ps=w, tns_ps=C["tt"].get("std_tns_max"), violators=C["tt"].get("std_nviol_max"),
            sdc_wns_ps=C["tt"].get("sdc_wns_max"), vclk_reference=ref,
            reason=None if v != "NOT RUN" else "TT vclk rebind to the routed pin-register mean unavailable")
    elif ok_corner("tt") and C["tt"].get("sdc_wns_max") is not None:
        w = C["tt"]["sdc_wns_max"]
        put("setup_tt", "PASS" if w >= 0 else "FAIL", wns_ps=w, tns_ps=C["tt"].get("sdc_tns_max"),
            violators=C["tt"].get("sdc_nviol_max"))
    else:
        put("setup_tt", "NOT RUN")
    # hold FF (standard overlay)
    if ok_corner("ff") and C["ff"].get("std_wns_min") is not None:
        w = C["ff"]["std_wns_min"]
        ov = C["ff"].get("overlay") or ""
        v = "PASS" if w >= 0 else "FAIL"
        # STD_* is printed even when the overlay could not be applied. In that
        # case it is only another raw-SDC measurement, not boundary-hold proof.
        reference = C["ff"].get("ff_vclk_reference")
        reference_ok = (requested == "sdc" or (reference or "").startswith("applied mode pin_flop_mean ")
                        or (requested == "bound-ff" and (reference or "").startswith("applied mode bound_ff ")))
        if not ov.startswith("applied ") or not reference_ok:
            v = "NOT RUN"
        why = None if v != "NOT RUN" else "standard boundary-hold overlay was not applied or requested FF clock reference was unavailable"
        ffr = ff_reference_problem(rec, C["ff"], requested)
        if ffr:
            v, why = "FAIL", ffr
        put("hold_ff", v, wns_ps=w, tns_ps=C["ff"].get("std_tns_min"), violators=C["ff"].get("std_nviol_min"),
            sdc_wns_ps=C["ff"].get("sdc_wns_min"), overlay=ov, ff_vclk_reference=reference, reason=why)
    else:
        put("hold_ff", "NOT RUN")
    if ok_corner("ss"):
        put("ss", "REPORT", setup_wns_ps=C["ss"].get("sdc_wns_max"), hold_wns_ps=C["ss"].get("std_wns_min"),
            slew_viol=C["ss"].get("slew_viol"), cap_viol=C["ss"].get("cap_viol"),
            label="SS: information only, never gates (AGENTS.md 2026-10-24)")
    # DRV at the sign-off corners
    done = [c for c in CORNERS if ok_corner(c)]
    if len(done) == len(CORNERS):
        bad = {c: dict(slew=C[c].get("slew_viol"), cap=C[c].get("cap_viol")) for c in done
               if (C[c].get("slew_viol") or 0) > 0 or (C[c].get("cap_viol") or 0) > 0
               or C[c].get("slew_viol") is None or C[c].get("cap_viol") is None}
        put("drv", "FAIL" if bad else "PASS", by_corner={c: dict(slew=C[c].get("slew_viol"), cap=C[c].get("cap_viol"))
                                                         for c in done}, failing=bad)
        fo = {c: C[c].get("fanout_viol") for c in done}
        put("fanout", "WARN" if any((v or 0) > 0 for v in fo.values()) else "PASS", limit=FANOUT_MAX,
            violators=fo, max_fanout=C[done[0]].get("fanout_max"), worst_net=C[done[0]].get("fanout_worst_net"))
        cs = C["tt"]["check_setup"]
        bad = {k: v for k, v in cs.items() if v and k in ("unconstrained", "unclocked", "loops")}
        put("unconstrained", "FAIL" if bad else "PASS", counts=cs)
    else:
        put("drv", "NOT RUN", corners_done=done)
        put("fanout", "NOT RUN")
        put("unconstrained", "NOT RUN")
    # clock
    if all(ok_corner(c) for c in SPREAD_CORNERS):
        sp, why = {}, []
        for c in [x for x in ALL_CORNERS if ok_corner(x)]:
            pf = C[c].get("insertion_pinflops")
            sp[c] = dict(pinflops=pf, all=C[c].get("insertion_all"), ck_errors=C[c].get("ck_errors"),
                         pair_skew=C[c].get("pair_skew"))
        for c in SPREAD_CORNERS:
            pf = C[c].get("insertion_pinflops")
            if not pf:
                why.append(f"{c.upper()}: no pin flops measured")
            ps = C[c].get("pair_skew") or {}
            checks = ps.get("checks", {})
            if not ps.get("done") or any(k not in checks for k in ("max", "min")):
                why.append(f"{c.upper()}: related pair skew NOT RUN")
            else:
                na = (ps.get("counts") or {}).get("no_clock_arrival") or 0
                if na > 0:
                    why.append(f"{c.upper()}: {int(na)} registers without a unique propagated clock arrival are "
                               f"missing from the related pair skew")
                for k, value in checks.items():
                    n, worst = value.get("n"), value.get("worst_abs_ps")
                    side = "setup" if k == "max" else "hold"
                    if not n or worst is None or not math.isfinite(worst):
                        why.append(f"{c.upper()} {side}: no finite related pair measurement")
                    elif worst > PAIR_SKEW_MAX_PS:
                        why.append(f"{c.upper()} {side} related pair skew {worst:.1f} ps > {PAIR_SKEW_MAX_PS:g} "
                                   f"({value.get('worst_launch')} -> {value.get('worst_capture')}"
                                   f"{', bound' if value.get('bounded') else ''})")
                    if (value.get("verify_ps") or 0.0) > PAIR_VERIFY_TOL_PS:
                        why.append(f"{c.upper()} {side}: pair skew path/arrival cross-check differs by "
                                   f"{value['verify_ps']:.2f} ps > {PAIR_VERIFY_TOL_PS:g} (measurement suspect)")
            if (C[c].get("ck_errors") or 0) > 0:
                why.append(f"{c.upper()}: {int(C[c]['ck_errors'])} register clock pins without a unique clock arrival")
        bound = dict(rec.get("policy", {}).get("insertion_bound") or {})
        if insertion_target is not None:
            bound["tt"] = insertion_target
        tol = float(bound.get("tol", INSERTION_TOL_PS))
        for c in ("tt", "ff"):          # FLOW 10-25: the routed I of each corner within tol of the bound I
            if bound.get(c) is None:
                continue
            pf = C[c].get("insertion_pinflops")
            if not pf:
                continue
            if abs(pf["mean"] - float(bound[c])) > tol:
                why.append(f"{c.upper()} pin-flop insertion {pf['mean']:.1f} ps not within bound {float(bound[c]):g} +- "
                           f"{tol:g}")
        put("clock", "FAIL" if why else "PASS", pair_skew_max_ps=PAIR_SKEW_MAX_PS, spread_info_only=True,
            by_corner=sp, problems=why,
            insertion_target_ps=insertion_target, insertion_bound=bound or None)
    else:
        put("clock", "NOT RUN")
    # macro liberty coverage (part of setup/hold validity)
    mm = {c: C[c].get("macro_missing") for c in done if C[c].get("macro_missing")}     # sign-off corners only
    if mm:
        put("macro_libs", "FAIL", missing=mm)
    for k in ("sdc_lint", "face_guard"):
        ch[k] = rec.get(k) or dict(verdict="NOT RUN")
    rc = rec.get("route") or {}
    put("drc", "NOT RUN" if rc.get("drc") is None else ("PASS" if rc["drc"] == 0 else "FAIL"),
        count=rc.get("drc"), source=rc.get("drc_source"))
    put("antenna", "NOT RUN" if rc.get("antenna_nets") is None else ("PASS" if rc["antenna_nets"] == 0 else "FAIL"),
        count=rc.get("antenna_nets"), source=rc.get("antenna_source"))
    reasons = []
    for k in BLOCKING + (("macro_libs",) if "macro_libs" in ch else ()):
        v = ch[k]["verdict"]
        if v != "PASS":
            reasons.append(f"{k}: {v}" + _detail(k, ch[k]))
    rec["checks"] = ch
    rec["reasons"] = reasons
    rec["verdict"] = "SIGNED" if not reasons else "NOT SIGNED"
    # Option-A local closure is provisional until its actual assembled parent
    # proves all assumed input ports. Legacy records take the identical path.
    ctx_file = (rec.get('inputs') or {}).get('sdc_lint_ctx')
    a_context = bool(ctx_file and Path(ctx_file).is_file() and
                     json.loads(Path(ctx_file).read_text()).get('hold_in_min_ports_ps'))
    if rec.get('io_hold') or a_context:
        from io_hold_qualification import apply_obligation
        apply_obligation(rec)
    return rec


def _detail(k, c):
    if k in ("setup_tt", "hold_ff") and c.get("wns_ps") is not None:
        r = f"; {c['reason']}" if k == "hold_ff" and str(c.get("reason") or "").startswith("FAIL_SIGNOFF") else ""
        return f" WNS {c['wns_ps']:+.2f} ps, {int(c.get('violators') or 0)} endpoints{r}"
    if k == "drv" and c.get("failing"):
        return " " + ", ".join(f"{x.upper()} slew {v['slew']} cap {v['cap']}" for x, v in c["failing"].items())
    if k == "unconstrained" and c.get("counts"):
        return " " + ", ".join(f"{a} {b}" for a, b in c["counts"].items() if b)
    if k == "clock" and c.get("problems"):
        return " " + "; ".join(c["problems"])
    if k == "sdc_lint" and c.get("n_errors"):
        return f" {c['n_errors']} errors (first: {c['errors'][0]})"
    if k == "face_guard":
        if c.get("fail_counts"):
            return f" {c['fail_counts']}"
        if c.get("reason"):
            return f" ({c['reason']})"
    if k in ("drc", "antenna") and c.get("count") is not None:
        return f" {c['count']} ({c.get('source')})"
    if k == "macro_libs":
        return f" {c.get('missing')}"
    return ""


def summary_line(rec):
    C = rec.get("checks", {})

    def g(k, f):
        return (C.get(k) or {}).get(f)
    pf, ps = {}, {}
    for c in ("tt", "ff"):
        x = ((((C.get("clock") or {}).get("by_corner") or {}).get(c) or {}).get("pinflops") or {})
        pf[c] = x.get("spread")
        ck = (((((C.get("clock") or {}).get("by_corner") or {}).get(c) or {}).get("pair_skew") or {}).get("checks") or {})
        w = [v.get("worst_abs_ps") for v in ck.values() if v.get("worst_abs_ps") is not None]
        ps[c] = max(w) if w else float("nan")
    return (f"{rec.get('name')}: {rec.get('verdict')} | TT setup {g('setup_tt', 'wns_ps')} | FF hold "
            f"{g('hold_ff', 'wns_ps')} (sdc {g('hold_ff', 'sdc_wns_ps')}) | SS setup (info) {g('ss', 'setup_wns_ps')} | "
            f"pair skew TT/FF {ps['tt']:.1f}/{ps['ff']:.1f} (spread info {pf['tt']}/{pf['ff']}) | DRC {g('drc', 'count')} ant {g('antenna', 'count')} | "
            f"sdc_lint {g('sdc_lint', 'verdict')} face_guard {g('face_guard', 'verdict')}")


# ---- CLI -----------------------------------------------------------------------------------------------------------
def cmd_run(a):
    base = Path(a.base).resolve() if a.base else find_base(a.run_dir)
    disc = discover(base, kit=a.kit, sdc=a.sdc, record=a.record)
    if not disc["sdc"]:
        raise SystemExit("signoff: no SDC (kit constraint.sdc / 6_final.sdc / --sdc)")
    disc["library_config"] = str(Path(a.library_config).resolve()) if getattr(a, "library_config", None) else None
    out = Path(a.out).resolve()
    core_contract = hard_core_latency_contract(disc)
    bound = None
    if core_contract:
        # COORD ruling 10-24: a hard core carries a core-latency contract -- its measured insertion is published
        # (core.json / the ETM max_clock_tree_path) and the parent tap balance subtracts it (early tap); the plan
        # 250 +- 40 target applies at the PARTITION tap, not inside the core.  Spread / unique-arrival still gate.
        # (ROOT-MERGE2 10-25: no FLOW per-corner insertion binding inside a hard-core contract kit either.)
        if a.insertion_target is not None:
            raise SystemExit("signoff: --insertion-target conflicts with the kit's hard-core latency contract")
        # FLOW-FIX 10-25 (COORD: no silent FF fallback to the SDC/TT vclk): a core kit whose sdc_lint ctx declares the
        # per-corner FF insertion (insertion_ff_ps: HBM / KV / QC core generators, the value the in-flow FF-only GRT
        # hold repair bound) times FF hold against that declared value ('bound-ff'); no rebind, no clock-check bound
        # (ROOT-MERGE2).  Without it the FF hold check FAILs ff_ref_missing.
        if getattr(a, "ff_bound_ps", None) is not None:                # explicit declared value (CLI-checked)
            disc["ff_bound_ps"] = float(a.ff_bound_ps)
        elif disc.get("sdc_lint_ctx"):
            lctx = json.loads(Path(disc["sdc_lint_ctx"]).read_text())
            if lctx.get("insertion_ff_ps") is not None and a.ff_vclk in ("auto", "bound-ff"):
                a.ff_vclk = "bound-ff"
                disc["ff_bound_ps"] = float(lctx["insertion_ff_ps"]) / float(lctx.get("time_unit_ps") or 1.0)
                a.ff_vclk_contract = a.ff_vclk_contract or f"declared core FF insertion {disc['sdc_lint_ctx']}"
    elif disc.get("sdc_lint_ctx"):                                  # die-plan kit: the bound (plan) insertion
        lctx = json.loads(Path(disc["sdc_lint_ctx"]).read_text())
        if a.insertion_target is None:
            a.insertion_target = float(lctx["insertion_ps"])
        if lctx.get("insertion_ff_ps") is not None:                 # FLOW 10-25 per-corner binding
            bound = dict(tt=float(lctx["insertion_ps"]), ff=float(lctx["insertion_ff_ps"]),
                         tol=float(lctx.get("insertion_tol_ps", INSERTION_TOL_PS)), source=disc["sdc_lint_ctx"])
    if a.ff_vclk == "auto":
        a.ff_vclk = "rebind" if bound else "sdc"
        if bound:
            a.ff_vclk_contract = a.ff_vclk_contract or f"kit per-corner insertion binding {bound['source']}"
    out.mkdir(parents=True, exist_ok=True)
    corners = [c for c in a.corners.split(",") if c]
    rec = dict(schema=SCHEMA, name=a.name or disc["design"] or base.name, generated=datetime.datetime.now()
               .astimezone().isoformat(timespec="seconds"), host=os.uname().nodename, inputs=disc,
               policy=dict(period_ps=PERIOD_PS, uncertainty_setup_ps=UNC_SETUP_PS, uncertainty_hold_ps=UNC_HOLD_PS,
                           spread_max_ps=SPREAD_MAX_PS, spread_corners=list(SPREAD_CORNERS),
                           insertion_tol_ps=INSERTION_TOL_PS, fanout_max=FANOUT_MAX,
                           ff_vclk=a.ff_vclk, ff_vclk_contract=a.ff_vclk_contract, insertion_bound=bound,
                           ff_vclk_bound_ps=disc.get("ff_bound_ps"),
                           hold_overlay="set_output_delay -min 0 / set_input_delay -min -40 vs the IO virtual clock",
                           derate="none in the verdict (60/25 ps uncertainty is the OCV+jitter margin); "
                                  "ocv5_* = flat late 1.05 / early 0.95, information only",
                           engine=f"OpenSTA in OpenROAD ({a.image}), one process per corner",
                           libs="Exact routed-kit ORFS make TC/BC_LIB_FILES; per-corner hashed receipt",
                           corner_rule="setup TT / hold FF / 60-25 ps / related pair skew CPPR <= 80 TT+FF; spread INFO; SS information only "
                                       "(owner 2026-10-24, AGENTS.md c7ce2ed69a)"),
               tool_commit=_git_head())
    with cf.ThreadPoolExecutor(len(corners)) as ex:
        futs = {c: ex.submit(run_corner, c, disc, out, a.image, a.docker, a.dry, a.ff_vclk) for c in corners}
        rec["corners"] = {c: f.result() for c, f in futs.items()}
    if a.dry:
        print(json.dumps(rec["corners"], indent=1))
        return 0
    ports = next((dict(clock_ports=x["clock_ports"], inputs=x["inputs"], outputs=x["outputs"])
                  for x in rec["corners"].values() if x.get("done")), None)
    rec["sdc_lint"] = run_sdc_lint(disc, ports) if ports else dict(verdict="NOT RUN", reason="no STA session finished")
    rec["face_guard"] = run_face_guard(disc, (ports or {}).get("clock_ports", ()))
    rec["route"] = route_counts(disc)
    evaluate(rec, a.insertion_target)
    if core_contract:
        rec["core_latency"] = dict(contract=core_contract, measured={
            c: rec["corners"][c].get("insertion_pinflops") for c in rec["corners"] if rec["corners"][c].get("done")})
        rec["checks"]["clock"]["core_latency_contract"] = core_contract.get("kind")
    (out / "signoff.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("SIGNOFF " + summary_line(rec))
    for r in rec["reasons"]:
        print(f"  - {r}")
    return 0 if rec["verdict"] == "SIGNED" else 1


def _git_head():
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def cmd_verdict(a):
    rec = json.loads(Path(a.record).read_text())
    evaluate(rec, a.insertion_target)
    print("SIGNOFF " + summary_line(rec))
    for r in rec["reasons"]:
        print(f"  - {r}")
    return 0 if rec["verdict"] == "SIGNED" else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--run-dir")
    g.add_argument("--base")
    r.add_argument("--kit")
    r.add_argument("--library-config", help="Explicit exact ORFS library-selection config for no-kit runs; macros resolve under its directory")
    r.add_argument("--sdc")
    r.add_argument("--record")
    r.add_argument("--name")
    r.add_argument("--out", required=True)
    r.add_argument("--corners", default=",".join(CORNERS))
    r.add_argument("--image", default=IMAGE)
    r.add_argument("--docker", default=os.environ.get("SIGNOFF_DOCKER", "sudo docker"))
    r.add_argument("--insertion-target", type=float)
    r.add_argument("--ff-vclk", choices=("auto",) + VCLK_MODES, default="auto",
                   help="IO virtual-clock reference: auto = rebind when the kit carries a per-corner insertion "
                        "binding (FLOW 10-25), else sdc; pin-flop-mean = opt-in FF-only measured reference")
    r.add_argument("--ff-vclk-contract", help="source-pinned measured core clock contract authorizing the FF reference")
    r.add_argument("--ff-bound-ps", type=float,
                   help="bound-ff: declared FF IO insertion (ps) for an already-routed core kit whose sdc_lint ctx has no "
                        "insertion_ff_ps; requires --ff-vclk bound-ff and --ff-vclk-contract naming its source")
    r.add_argument("--dry", action="store_true")
    v = sub.add_parser("verdict")
    v.add_argument("record")
    v.add_argument("--insertion-target", type=float)
    a = ap.parse_args(argv)
    if a.cmd == "run" and a.ff_bound_ps is not None and a.ff_vclk != "bound-ff":
        ap.error("--ff-bound-ps requires --ff-vclk bound-ff")
    if a.cmd == "run" and a.ff_bound_ps is not None and not (a.ff_vclk_contract or "").strip():
        ap.error("--ff-bound-ps requires --ff-vclk-contract (source of the declared FF insertion)")
    if a.cmd == "run" and a.ff_vclk == "pin-flop-mean" and not (a.ff_vclk_contract or "").strip():
        ap.error("--ff-vclk pin-flop-mean requires --ff-vclk-contract (measured core clock contract)")
    return cmd_run(a) if a.cmd == "run" else cmd_verdict(a)


if __name__ == "__main__":
    sys.exit(main())
