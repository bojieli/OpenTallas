#!/usr/bin/env python3
"""Closure-loop calibrate stage: measure a block's real clock insertion after CTS, at SS, TT and FF.

Reads <base>/4_1_cts.odb (+ its SDC: 4_cts.sdc, else 3_place.sdc) with placement-estimated parasitics (or a routed
6_final.odb + SPEF if --routed), propagates clocks and reports, per corner, the clock arrival of the ACTIVE edge (FLOW-FIX-0410) at the CLK pins of
(a) BOUNDARY registers -- registers whose D is in the fan-out of a data input, or whose output reaches a data output,
i.e. the flops the IO SDC really talks to -- and (b) every register of the clock.  mean / min / max in ps.  Read-only
on the ORFS dir (Tcl in a temp dir).  Writes JSON and prints shell assignments (CK_SS_MEAN=.. CK_FF_MIN=..) that the
closure loop exports into every later stage of the job (boundary values; *_ALL_* for all registers).

    ck_insertion.py --base RUN/work/orfs/results/asap7/<design>/base [--clock ck] [--routed] [--route-corner TC]
                    --output calib.json

ROUTE CORNER (calib-corner 2026-10-08): every recipe's route-time IO SDC is generated from CK_SS_* (io_vclk_m_$CK_SS_MEAN,
make_sdc.py --l-ss-*, budget SDCs).  A route at --route-corner TC/TT is setup-repaired at TT and signed off at the routed
TT reference, so CK_SS_* then carry the TT (route-corner) insertion; the SS-library values move to CK_SSLIB_*
(CK_TT_* always hold the TT values, CK_ROUTE_REF names the reference).  Before this, a TC route referenced its outputs
to the SS insertion (~190 ps above the TT boundary insertion): the router saw output setup credit sign-off removed
(orphans-2 hfd_router: route -71.83 -> routed reference -152.67).
"""
import argparse, json, re, subprocess, tempfile
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"

# FLOW-FIX-0410 2026-10-09: the arrival of the sink's ACTIVE transition (from-transition of its clock->output arc),
# measured from the source edge that produces it, on the rise-edge time base (an arrival from the source FALL edge has
# the half period removed).  Same rule as physical/common_flow/io_ref_routed.sdc: behind an odd clock inversion
# (ot_fwd_link_stage, fck = ~ck) arrival_max_rise is T/2 + tree (dsfd_hstnh_515: 603 vs ~190 ps).
ACTIVE_TCL = r"""
set ::ot_ck_act [dict create]
proc ot_ck_active {p} {
  set c [get_cells -quiet -of_objects $p]
  if {![llength $c]} { return "" }
  set k "[get_property $c ref_name]/[get_property $p lib_pin_name]"
  if {[dict exists $::ot_ck_act $k]} { return [dict get $::ot_ck_act $k] }
  sta::redirect_string_begin
  catch {report_edges -from $p}
  set r [sta::redirect_string_end]
  set on 0; set fr {}
  foreach l [split $r "\n"] {
    if {[regexp {^\S} $l]} { set on [regexp {(Clk|En) to Q} $l]; continue }
    if {$on && [regexp {^\s+([\^v])\s+->} $l -> e]} { if {[lsearch -exact $fr $e] < 0} { lappend fr $e } }
  }
  set a [expr {[llength $fr] == 1 ? ([lindex $fr 0] eq "^" ? "r" : "f") : ""}]
  dict set ::ot_ck_act $k $a
  return $a
}
proc ot_ck_arr {p clk} {
  set half 0.0
  if {![catch {list [$clk waveform] [$clk period] [get_property $clk period]} w]} {
    lassign $w wf ps pu
    if {[llength $wf] >= 2 && $ps > 0} { set half [expr {([lindex $wf 1] - [lindex $wf 0]) * $pu / $ps}] } }
  set ar [get_property $p arrival_max_rise]; set af [get_property $p arrival_max_fall]
  set okr [string is double -strict $ar]; set okf [string is double -strict $af]
  if {!($okr && $okf)} { return [expr {$okr ? $ar : ($okf ? $af : "")}] }
  set t [ot_ck_active $p]
  set lo [expr {$ar <= $af ? "r" : "f"}]
  if {$t eq ""} { set t $lo }
  set v [expr {$t eq "r" ? $ar : $af}]
  return [expr {$t eq $lo ? $v : $v - $half}]
}
"""


def tcl(corner, db, sdc, routed, clock):
    C = corner.upper()
    par = "read_spef /base/6_final.spef" if routed else f"source {PLAT}/setRC.tcl\nestimate_parasitics -placement"
    return f"""
foreach l [glob {PLAT}/lib/NLDM/*RVT_{C}*] {{ read_liberty $l }}
foreach l [glob {PLAT}/lib/NLDM/*_LVT_{C}_* {PLAT}/lib/NLDM/*_SLVT_{C}_*] {{ if {{![string match *FAKE* $l]}} {{ read_liberty $l }} }}
read_db /base/{db}
read_sdc /base/{sdc}
{par}
set_propagated_clock [all_clocks]
set regs {{}}
foreach p [all_registers -clock_pins -clock [get_clocks {{{clock}}}]] {{ set n [get_full_name $p]; dict set regs [regsub {{/[^/]+$}} $n {{}}] $n }}
set bnd {{}}
set din [all_inputs -no_clocks]
if {{[llength $din]}} {{ foreach pe [find_timing_paths -path_delay max -from $din -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {{ set i [regsub {{/[^/]+$}} [get_full_name [get_property $pe endpoint]] {{}}]; if {{[dict exists $regs $i]}} {{ dict set bnd $i 1 }} }} }}
foreach pe [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {{ set i [regsub {{/[^/]+$}} [get_full_name [get_property $pe startpoint]] {{}}]; if {{[dict exists $regs $i]}} {{ dict set bnd $i 1 }} }}
{ACTIVE_TCL}
set ot_ck_clk [lindex [get_clocks {{{clock}}}] 0]
dict for {{i cp}} $regs {{
  set a [ot_ck_arr [get_pins $cp] $ot_ck_clk]
  if {{$a eq "" || $a eq "INF" || $a eq "-INF"}} continue
  puts "OT_CK [expr {{[dict exists $bnd $i] ? 1 : 0}}] $a"
}}
exit
"""


def stats(v):
    return dict(n=len(v), mean=round(sum(v) / len(v), 1), min=round(min(v), 1), max=round(max(v), 1)) if v else None


def route_env(env, route_corner):
    """CK_SS_* = the route-corner setup insertion (TT for TC/TT routes; SS values kept as CK_SSLIB_*)"""
    env = dict(env)
    if str(route_corner or "").upper() in ("TC", "TT"):
        if "CK_TT_MEAN" not in env:
            raise SystemExit(f"route corner {route_corner}: no TT insertion measured")
        for k in ("MEAN", "MIN", "MAX", "ALL_MEAN", "ALL_MIN", "ALL_MAX"):
            if f"CK_SS_{k}" in env:
                env[f"CK_SSLIB_{k}"] = env[f"CK_SS_{k}"]
            env[f"CK_SS_{k}"] = env[f"CK_TT_{k}"]
        env["CK_ROUTE_REF"] = "TT"
    else:
        env["CK_ROUTE_REF"] = "SS"
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--clock", default="ck")
    ap.add_argument("--routed", action="store_true")
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--route-corner", default="", help="TC/TT: CK_SS_* carry the TT insertion (route-time IO reference)")
    a = ap.parse_args()
    base = a.base.resolve()
    if a.routed:
        db, sdc = "6_final.odb", "6_final.sdc"
    else:
        db = "4_1_cts.odb"
        sdc = next((s for s in ("4_cts.sdc", "3_place.sdc", "2_floorplan.sdc", "1_synth.sdc") if (base / s).exists()), None)
        if not (base / db).exists() or not sdc:
            raise SystemExit(f"no {db} / SDC under {base}")
    rec = dict(schema="opentallas.closure_loop.ck_insertion.v1", base=str(base), db=db, sdc=sdc, clock=a.clock,
               parasitics="spef" if a.routed else "placement-estimated")
    env = {}
    need_tt = a.route_corner.upper() in ("TC", "TT")
    for corner in ("ss", "tt", "ff"):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "s.tcl").write_text(tcl(corner, db, sdc, a.routed, a.clock))
            out = subprocess.run(["docker", "run", "--rm", "-v", f"{base}:/base:ro", "-v", f"{td}:/t:ro", a.image, "bash",
                                  "-lc", "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl"],
                                 capture_output=True, text=True).stdout
        b, al = [], []
        for m in re.finditer(r"^OT_CK (\d) (\S+)", out, re.M):
            x = float(m[2])
            al.append(x)
            if m[1] == "1":
                b.append(x)
        rec[corner] = dict(boundary=stats(b), all=stats(al), errors=re.findall(r"\[ERROR[^\n]*", out)[:5])
        if not al and corner == "tt" and not need_tt:
            continue                     # TT is informational for an SS-corner route
        if not al:
            raise SystemExit(f"{corner}: no clock arrivals for clock {a.clock}\n{out[-1500:]}")
        bs = rec[corner]["boundary"] or rec[corner]["all"]
        for k in ("mean", "min", "max"):
            env[f"CK_{corner.upper()}_{k.upper()}"] = round(bs[k])
            env[f"CK_{corner.upper()}_ALL_{k.upper()}"] = round(rec[corner]["all"][k])
    env = route_env(env, a.route_corner)
    rec["route_corner"] = a.route_corner or None
    rec["env"] = env
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(" ".join(f"{k}={v}" for k, v in env.items()))


if __name__ == "__main__":
    main()
