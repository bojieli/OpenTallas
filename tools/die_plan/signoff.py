#!/usr/bin/env python3
"""Uniform sign-off of a closed block (lane SIGNOFF, 2026-10-24): one recipe applied to every block before it is
called closed.  Past "closed" records came from many lanes and flows: some were not die-bindable (pin-flop spread
> 80 ps), kit SDCs before main 4b7b2b3e64 waived the sender seam hold (no set_output_delay -min), and 27 of 43 tiles
once "closed" were unassemblable (docs/LESSONS_ARCH_PHYSICAL_1012.md).  This tool re-signs a block from its ROUTED
data only, with the same checks for everyone.

    signoff.py run (--run-dir ORFS_RUN | --base RESULTS_BASE) [--kit KITDIR] [--sdc SDC] [--name N] --out DIR
                   [--corners ss,ff,tt] [--image IMG] [--insertion-target PS] [--record gate_result.json]
    signoff.py verdict DIR/signoff.json           # re-evaluate a record (exit 0 SIGNED, 1 NOT SIGNED)

INPUTS: the routed ODB (<base>/6_final.odb) and its SPEF (<base>/6_final.spef; when absent the parasitics are
re-extracted with OpenRCX: extract_parasitics -ext_model_file asap7 rcx_patterns.rules, recorded as 'rcx').  The
golden SDC is the kit's constraint.sdc (KIT = parent of the ORFS run dir) unless --sdc; else <base>/6_final.sdc.
Macro / hard-child liberty files come from the kit config.mk ADDITIONAL_LIBS (/work = KIT), per corner (_ss/_ff/_tt).

ENGINE: OpenSTA as built into OpenROAD in the pinned ORFS image (openroad/orfs:latest = :asap7lock), one process per
corner (MCMM = 3 corners x 1 functional mode, run in parallel), ASAP7 NLDM RVT+LVT+SLVT liberty of that corner.

CHECKS (each PASS / FAIL / NOT RUN; SIGNED only if every blocking check PASSes):
  setup_ss      SS setup WNS >= 0 (AGENTS.md: a headline clock closes setup at SS)                       blocking
  hold_ff       FF hold WNS >= 0 under the STANDARD boundary-hold overlay                                  blocking
                (set_output_delay -min 0 and set_input_delay -min -insertion_tol (40 ps) on every data port vs the
                IO virtual clock: the 4b7b2b3e64 kit standard; the raw-SDC hold is reported as hold_ff_sdc)
  tt            TT setup / hold reported (pathfinding only, labelled TT)                                   report
  uncertainty   the SDC carries 60 ps setup / 25 ps hold (sdc_lint 'uncertainty'), period = 833 ps     (in sdc_lint)
  drv           max transition and max capacitance violations = 0 at SS, FF and TT (liberty limits)        blocking
  fanout        nets with fanout > FANOUT_MAX (64; ASAP7 liberty has no max_fanout)                        WARN only
  unconstrained check_setup -unconstrained_endpoints = 0, no unclocked registers, no loops                blocking
  clock         per corner: active-edge clock arrival at every register clock pin (insertion min/mean/max) and
                at the PIN FLOPS (registers whose D is in the fan-out of a data input or whose Q reaches a data
                output); pin-flop spread = max - min <= 80 ps at TT and FF (R4, COORD 10-23); with
                --insertion-target the pin-flop mean must be within +-insertion_tol                         blocking
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
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

SCHEMA = "opentallas.signoff.v1"
IMAGE = os.environ.get("ORFS_IMAGE", "openroad/orfs:latest")
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
PERIOD_PS = 833.0
UNC_SETUP_PS, UNC_HOLD_PS = 60.0, 25.0
INSERTION_PS, INSERTION_TOL_PS = 250.0, 40.0
SPREAD_MAX_PS = 80.0
FANOUT_MAX = 64
SPREAD_CORNERS = ("tt", "ff")
CORNERS = ("ss", "ff", "tt")
BLOCKING = ("setup_ss", "hold_ff", "drv", "unconstrained", "clock", "sdc_lint", "face_guard", "drc", "antenna")


# ---- discovery ----------------------------------------------------------------------------------------------------
def find_base(run_dir):
    """<run>/results/asap7/<design>/base (exactly one) or run_dir itself if it holds 6_final.odb."""
    rd = Path(run_dir)
    if (rd / "6_final.odb").is_file():
        return rd
    for pat in ("results/asap7/*/base", "run/results/asap7/*/base", "work/orfs/results/asap7/*/base"):
        hits = sorted(p for p in rd.glob(pat) if (p / "6_final.odb").is_file())
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise SystemExit(f"signoff: several routed bases under {rd}: {hits}")
    raise SystemExit(f"signoff: no results/asap7/*/base/6_final.odb under {rd}")


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
             odb=str(base / "6_final.odb"), spef=None, sdc=None, sdc_source=None, synth=None, final_v=None,
             metrics={}, drc_rpt=None, pins=None, sdc_lint_ctx=None, record=str(record) if record else None)
    if (base / "6_final.spef").is_file():
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
    """(host paths of the corner's macro liberty files, missing corner list) from KIT/config.mk ADDITIONAL_LIBS."""
    if not kit or not (Path(kit) / "config.mk").is_file():
        return [], []
    txt = (Path(kit) / "config.mk").read_text(errors="replace").replace("\\\n", " ")
    libs, missing = [], []
    for m in re.finditer(r"^\s*(?:export\s+)?ADDITIONAL_LIBS\s*[:+?]?=\s*(.*)$", txt, re.M):
        for w in m.group(1).split():
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
            elif p.is_file() and corner == "tt":
                cand = p
            if cand is None:
                missing.append(f"{p.name} ({corner})")
            else:
                libs.append(str(cand))
    return libs, missing


# ---- the OpenSTA session (one corner) -----------------------------------------------------------------------------
def _clock_family_tcl():
    p = REPO / "physical/common_flow/clock_family.tcl"
    return p.read_text() if p.is_file() else ""


SESSION_TCL = r"""
proc so {k args} { puts "SO $k [join $args { }]" }
proc so_ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.2f [sta::time_sta_ui $t]] }
foreach l [glob @PLAT@/lib/NLDM/*_RVT_@C@_*] { read_liberty $l }
foreach l [glob -nocomplain @PLAT@/lib/NLDM/*_LVT_@C@_* @PLAT@/lib/NLDM/*_SLVT_@C@_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
@MACRO_LIBS@
read_db /base/6_final.odb
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
if {[llength $so_vclk] == 1} {
  if {[llength $so_din]} { set_input_delay -min [expr {-@INS_TOL@}] -clock [lindex $so_vclk 0] $so_din }
  if {[llength [all_outputs]]} { set_output_delay -min 0 -clock [lindex $so_vclk 0] [all_outputs] }
  so OVERLAY applied [get_full_name [lindex $so_vclk 0]] in_min -@INS_TOL@ out_min 0
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
# ---- clock: active-edge arrival at register clock pins, pin flops ----
@CLOCK_FAMILY@
set so_regs {}
foreach p [all_registers -clock_pins] { dict set so_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
set so_bnd {}
set so_data {}
set so_async {}
foreach p [all_registers -async_pins] { dict set so_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] { set n [get_full_name $p]; if {![dict exists $so_async $n]} { dict set so_data $n 1 } }
if {[llength $so_din]} {
  foreach p [get_fanout -from $so_din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $so_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $so_regs $i]} { dict set so_bnd $i 1 }
  }
}
if {[llength [all_outputs]]} {
  foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $so_regs $i]} { dict set so_bnd $i 1 }
  }
}
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
    catch {set a [sta::time_sta_ui [get_property $p arrival_max_rise]]}
  }
  if {$a eq "" || ![string is double -strict $a]} { incr so_ck_err; continue }
  puts "SO_CK [expr {[dict exists $so_bnd $i] ? 1 : 0}] [format %.2f $a] [get_full_name [lindex $cl 0]]"
}
so CK_ERRORS $so_ck_err
so DONE 1
exit
"""


def session_tcl(corner, mlibs_ctr, spef, ins_tol=INSERTION_TOL_PS, fanout_max=FANOUT_MAX):
    if spef:
        par, src = "read_spef /base/6_final.spef", "spef"
    else:
        par, src = (f"source {PLAT}/setRC.tcl\nextract_parasitics -ext_model_file {PLAT}/rcx_patterns.rules\n"
                    "write_spef /out/rcx.spef\nread_spef /out/rcx.spef"), "rcx"
    t = SESSION_TCL
    for k, v in (("@PLAT@", PLAT), ("@C@", corner.upper()), ("@PARASITICS@", par), ("@PARSRC@", src),
                 ("@MACRO_LIBS@", "\n".join(f"read_liberty {x}" for x in mlibs_ctr)),
                 ("@INS_TOL@", f"{ins_tol:g}"), ("@FANOUT_MAX@", str(int(fanout_max))),
                 ("@CLOCK_FAMILY@", _clock_family_tcl())):
        t = t.replace(k, v)
    return t


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
               outputs=(kv.get("OUTPUTS") or "").split(), overlay=kv.get("OVERLAY"))
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
    out["ocv5_wns_max"] = _f(kv.get("OCV5_WNS_MAX"))
    out["ocv5_wns_min"] = _f(kv.get("OCV5_WNS_MIN"))
    return out


def run_corner(corner, disc, out, image=IMAGE, docker="sudo docker", dry=False):
    od = Path(out) / corner
    od.mkdir(parents=True, exist_ok=True)
    mlibs, mmiss = macro_libs(disc["kit"], corner)
    mounts = [("base", disc["base"]), ("sdc", str(od / "sdcdir")), ("out", str(od))]
    (od / "sdcdir").mkdir(exist_ok=True)
    (od / "sdcdir" / "golden.sdc").write_text(Path(disc["sdc"]).read_text())
    ml_ctr = []
    for i, lp in enumerate(mlibs):
        mounts.append((f"ml{i}", str(Path(lp).parent)))
        ml_ctr.append(f"/ml{i}/{Path(lp).name}")
    (od / "session.tcl").write_text(session_tcl(corner, ml_ctr, disc["spef"]))
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


def run_face_guard(disc, clock_ports=()):
    import face_guard
    if not disc.get("synth"):
        return dict(verdict="NOT RUN", reason="no synthesized netlist (1_synth.v / 1_2_yosys.v) in the routed base")
    pins = json.loads(Path(disc["pins"]).read_text()) if disc.get("pins") else None
    if isinstance(pins, dict):
        pins = pins.get("pins")
    if pins is not None and not (isinstance(pins, list) and pins and isinstance(pins[0], dict) and "bus" in pins[0]):
        pins = None
    skip = sorted(set(clock_ports) | {"arst_n"})
    skip_re = r"^(clk(_t[0-9]+)?|" + "|".join(re.escape(x) for x in skip) + r")$"
    if pins is not None:                      # the clock / reset pins are not face registers
        pins = [x for x in pins if not re.match(skip_re, str(x.get("bus")))]
    try:
        r = face_guard.guard(Path(disc["synth"]).read_text(errors="replace"), pins=pins, skip_re=skip_re)
    except Exception as e:
        return dict(verdict="NOT RUN", reason=f"face_guard error: {e}", netlist=disc["synth"])
    return dict(verdict=r["verdict"], top=r.get("top"), checked=r.get("checked"), ok=r.get("ok"),
                fail_counts=r.get("fail_counts"), fails={k: v[:5] for k, v in (r.get("fails") or {}).items()},
                netlist=disc["synth"], pins=disc.get("pins"))


# ---- verdict -------------------------------------------------------------------------------------------------------
def evaluate(rec, insertion_target=None):
    """fills rec['checks'] and rec['verdict'] / rec['reasons'] from rec['corners'] + record checks."""
    C = rec.get("corners", {})
    ch = {}

    def ok_corner(c):
        x = C.get(c)
        return x is not None and x.get("done")

    def put(name, verdict, **kw):
        ch[name] = dict(verdict=verdict, **kw)

    # setup SS
    if ok_corner("ss") and C["ss"].get("sdc_wns_max") is not None:
        w = C["ss"]["sdc_wns_max"]
        put("setup_ss", "PASS" if w >= 0 else "FAIL", wns_ps=w, tns_ps=C["ss"].get("sdc_tns_max"),
            violators=C["ss"].get("sdc_nviol_max"))
    else:
        put("setup_ss", "NOT RUN")
    # hold FF (standard overlay)
    if ok_corner("ff") and C["ff"].get("std_wns_min") is not None:
        w = C["ff"]["std_wns_min"]
        ov = C["ff"].get("overlay") or ""
        v = "PASS" if w >= 0 else "FAIL"
        if not ov.startswith("applied"):
            v = "FAIL" if w < 0 else "PASS"
        put("hold_ff", v, wns_ps=w, tns_ps=C["ff"].get("std_tns_min"), violators=C["ff"].get("std_nviol_min"),
            sdc_wns_ps=C["ff"].get("sdc_wns_min"), overlay=ov)
    else:
        put("hold_ff", "NOT RUN")
    if ok_corner("tt"):
        put("tt", "REPORT", setup_wns_ps=C["tt"].get("sdc_wns_max"), hold_wns_ps=C["tt"].get("std_wns_min"),
            hold_sdc_wns_ps=C["tt"].get("sdc_wns_min"), label="TT: pathfinding only")
    else:
        put("tt", "NOT RUN")
    # DRV
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
        cs = C["ss"]["check_setup"]
        bad = {k: v for k, v in cs.items() if v and k in ("unconstrained", "unclocked", "loops")}
        put("unconstrained", "FAIL" if bad else "PASS", counts=cs)
    else:
        put("drv", "NOT RUN", corners_done=done)
        put("fanout", "NOT RUN")
        put("unconstrained", "NOT RUN")
    # clock
    if all(ok_corner(c) for c in SPREAD_CORNERS):
        sp, why = {}, []
        for c in done:
            pf = C[c].get("insertion_pinflops")
            sp[c] = dict(pinflops=pf, all=C[c].get("insertion_all"), ck_errors=C[c].get("ck_errors"))
        for c in SPREAD_CORNERS:
            pf = C[c].get("insertion_pinflops")
            if not pf:
                why.append(f"{c.upper()}: no pin flops measured")
            elif pf["spread"] > SPREAD_MAX_PS:
                why.append(f"{c.upper()} pin-flop spread {pf['spread']:.1f} ps > {SPREAD_MAX_PS:g}")
            if (C[c].get("ck_errors") or 0) > 0:
                why.append(f"{c.upper()}: {int(C[c]['ck_errors'])} register clock pins without a unique clock arrival")
        if insertion_target is not None:
            pf = C["tt"].get("insertion_pinflops")
            if pf and abs(pf["mean"] - insertion_target) > INSERTION_TOL_PS:
                why.append(f"TT pin-flop insertion {pf['mean']:.1f} ps not within {insertion_target:g} +- "
                           f"{INSERTION_TOL_PS:g}")
        put("clock", "FAIL" if why else "PASS", spread_max_ps=SPREAD_MAX_PS, by_corner=sp, problems=why,
            insertion_target_ps=insertion_target)
    else:
        put("clock", "NOT RUN")
    # macro liberty coverage (part of setup/hold validity)
    mm = {c: C[c].get("macro_missing") for c in done if C[c].get("macro_missing")}
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
    return rec


def _detail(k, c):
    if k in ("setup_ss", "hold_ff") and c.get("wns_ps") is not None:
        return f" WNS {c['wns_ps']:+.2f} ps, {int(c.get('violators') or 0)} endpoints"
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
    pf = {}
    for c in ("tt", "ff"):
        x = ((((C.get("clock") or {}).get("by_corner") or {}).get(c) or {}).get("pinflops") or {})
        pf[c] = x.get("spread")
    return (f"{rec.get('name')}: {rec.get('verdict')} | SS setup {g('setup_ss', 'wns_ps')} | FF hold "
            f"{g('hold_ff', 'wns_ps')} (sdc {g('hold_ff', 'sdc_wns_ps')}) | TT setup {g('tt', 'setup_wns_ps')} | "
            f"spread TT/FF {pf['tt']}/{pf['ff']} | DRC {g('drc', 'count')} ant {g('antenna', 'count')} | "
            f"sdc_lint {g('sdc_lint', 'verdict')} face_guard {g('face_guard', 'verdict')}")


# ---- CLI -----------------------------------------------------------------------------------------------------------
def cmd_run(a):
    base = Path(a.base).resolve() if a.base else find_base(a.run_dir)
    disc = discover(base, kit=a.kit, sdc=a.sdc, record=a.record)
    if not disc["sdc"]:
        raise SystemExit("signoff: no SDC (kit constraint.sdc / 6_final.sdc / --sdc)")
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    corners = [c for c in a.corners.split(",") if c]
    rec = dict(schema=SCHEMA, name=a.name or disc["design"] or base.name, generated=datetime.datetime.now()
               .astimezone().isoformat(timespec="seconds"), host=os.uname().nodename, inputs=disc,
               policy=dict(period_ps=PERIOD_PS, uncertainty_setup_ps=UNC_SETUP_PS, uncertainty_hold_ps=UNC_HOLD_PS,
                           spread_max_ps=SPREAD_MAX_PS, spread_corners=list(SPREAD_CORNERS),
                           insertion_tol_ps=INSERTION_TOL_PS, fanout_max=FANOUT_MAX,
                           hold_overlay="set_output_delay -min 0 / set_input_delay -min -40 vs the IO virtual clock",
                           derate="none in the verdict (60/25 ps uncertainty is the OCV+jitter margin); "
                                  "ocv5_* = flat late 1.05 / early 0.95, information only",
                           engine=f"OpenSTA in OpenROAD ({a.image}), one process per corner",
                           libs="ASAP7 NLDM RVT+LVT+SLVT per corner + kit ADDITIONAL_LIBS per corner"),
               tool_commit=_git_head())
    with cf.ThreadPoolExecutor(len(corners)) as ex:
        futs = {c: ex.submit(run_corner, c, disc, out, a.image, a.docker, a.dry) for c in corners}
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
    r.add_argument("--sdc")
    r.add_argument("--record")
    r.add_argument("--name")
    r.add_argument("--out", required=True)
    r.add_argument("--corners", default=",".join(CORNERS))
    r.add_argument("--image", default=IMAGE)
    r.add_argument("--docker", default=os.environ.get("SIGNOFF_DOCKER", "sudo docker"))
    r.add_argument("--insertion-target", type=float)
    r.add_argument("--dry", action="store_true")
    v = sub.add_parser("verdict")
    v.add_argument("record")
    v.add_argument("--insertion-target", type=float)
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else cmd_verdict(a)


if __name__ == "__main__":
    sys.exit(main())
