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

MACRO-CLK (macro-clk-1010, 2026-10-10): the same session also measures every memory macro's clock pin (macro liberty read
from the route's config.mk, /src = the job snapshot): active-edge arrival and slew per corner, and judges outliers
(macro_outliers): slew above MC_SLEW_PS at any corner, or the FF arrival more than MC_LATE_PS after the register mean
(the SRAM wd_in / addr hold stall of ds-1010 lcrph: one shallow macro leaf, 165-260 ps slew, ~60 ps late).  The verdict is
rec["macro_clk"]; the closure loop flags it after CTS and its auto-react class f reads it.
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


def tcl(corner, db, sdc, routed, clock, mlibs=()):
    C = corner.upper()
    ml = "\n".join(f"read_liberty {l}" for l in mlibs)
    par = "read_spef /base/6_final.spef" if routed else f"source {PLAT}/setRC.tcl\nestimate_parasitics -placement"
    return f"""
foreach l [glob {PLAT}/lib/NLDM/*RVT_{C}*] {{ read_liberty $l }}
foreach l [glob {PLAT}/lib/NLDM/*_LVT_{C}_* {PLAT}/lib/NLDM/*_SLVT_{C}_*] {{ if {{![string match *FAKE* $l]}} {{ read_liberty $l }} }}
{ml}
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
foreach inst [[ord::get_db_block] getInsts] {{
  if {{![[$inst getMaster] isBlock]}} continue
  foreach it [$inst getITerms] {{
    set n [$it getNet]
    if {{$n eq "NULL" || $n eq ""}} continue
    if {{[[$it getMTerm] getSigType] ne "CLOCK" && [$n getSigType] ne "CLOCK"}} continue
    set p [get_pins -quiet "[$inst getName]/[[$it getMTerm] getName]"]
    if {{![llength $p]}} continue
    set a [ot_ck_arr $p $ot_ck_clk]
    set sl [get_property $p slew_max_rise]
    if {{$a eq "" || $a eq "INF" || $a eq "-INF" || ![string is double -strict $sl]}} continue
    puts "OT_MC [get_full_name $p] $a $sl [$n getName]"
  }}
}}
exit
"""


MC_SLEW_PS = 120.0    # macro clock-pin slew bound (any corner); register clock pins sit at ~20-50 ps on ASAP7
MC_LATE_PS = 30.0     # FF macro clock arrival after the register mean: the SRAM data / addr hold deficit grows 1:1
LIB_RE = re.compile(r"(/src/\S+?)_(ss|tt|ff)\.lib\b")


def macro_libs(base, corner):
    """(host source root, [/src/... macro liberty paths for corner]) from the route's config.mk, else (None, [])"""
    base = Path(base)
    cfg = next((p / "config.mk" for p in base.parents if (p / "config.mk").is_file()), None)
    if cfg is None:
        return None, []
    stems = sorted({m.group(1) for m in LIB_RE.finditer(cfg.read_text(errors="replace"))})
    if not stems:
        return None, []
    rel = f"{stems[0][len('/src/'):]}_{corner}.lib"
    root = next((r for p in base.parents for r in (p / "src", p) if (r / rel).is_file()), None)
    if root is None:
        return None, []
    return root, [f"{x}_{corner}.lib" for x in stems if (root / f"{x[len('/src/'):]}_{corner}.lib").is_file()]


def macro_summary(rows, reg_mean):
    """per-corner macro clock-pin record: rows = [(pin, arrival, slew, net)]"""
    if not rows:
        return None
    pins = [dict(pin=p, arr=round(a, 1), slew=round(sl, 1), late=round(a - reg_mean, 1) if reg_mean is not None else None,
                 net=n) for p, a, sl, n in rows]
    nets = {}
    for x in pins:
        nets[x["net"]] = nets.get(x["net"], 0) + 1
    return dict(n=len(pins), nets=len(nets), max_per_net=max(nets.values()), reg_mean=reg_mean,
                max_slew=max(x["slew"] for x in pins),
                max_late=max((x["late"] for x in pins if x["late"] is not None), default=None), pins=pins)


def macro_outliers(rec, slew_ps=MC_SLEW_PS, late_ps=MC_LATE_PS):
    """the MACRO-CLK verdict: {"n", "outliers": [{pin, why}], "flag": bool} from the per-corner macro records"""
    out, n = {}, 0
    for corner in ("ss", "tt", "ff"):
        m = (rec.get(corner) or {}).get("macros")
        if not m:
            continue
        n = max(n, m["n"])
        for x in m["pins"]:
            why = []
            if x["slew"] > slew_ps:
                why.append(f"{corner} slew {x['slew']:.0f} ps > {slew_ps:.0f}")
            if corner == "ff" and x["late"] is not None and x["late"] > late_ps:
                why.append(f"ff {x['late']:.0f} ps after the register mean > {late_ps:.0f}")
            if why:
                out.setdefault(x["pin"], []).extend(why)
    return dict(n=n, slew_ps=slew_ps, late_ps=late_ps, flag=bool(out),
                outliers=[dict(pin=k, why="; ".join(v)) for k, v in sorted(out.items())])


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
        sroot, mlibs = macro_libs(base, corner)
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "s.tcl").write_text(tcl(corner, db, sdc, a.routed, a.clock, mlibs))
            mnt = ["-v", f"{sroot}:/src:ro"] if sroot else []
            out = subprocess.run(["docker", "run", "--rm", "-v", f"{base}:/base:ro", "-v", f"{td}:/t:ro", *mnt, a.image,
                                  "bash", "-lc",
                                  "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl"],
                                 capture_output=True, text=True).stdout
        b, al = [], []
        for m in re.finditer(r"^OT_CK (\d) (\S+)", out, re.M):
            x = float(m[2])
            al.append(x)
            if m[1] == "1":
                b.append(x)
        mrows = [(m[1], float(m[2]), float(m[3]), m[4])
                 for m in re.finditer(r"^OT_MC (\S+) (\S+) (\S+) (\S+)", out, re.M)]
        rec[corner] = dict(boundary=stats(b), all=stats(al), errors=re.findall(r"\[ERROR[^\n]*", out)[:5],
                           macros=macro_summary(mrows, round(sum(al) / len(al), 1) if al else None),
                           macro_libs=len(mlibs))
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
    rec["macro_clk"] = macro_outliers(rec)
    rec["env"] = env
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(" ".join(f"{k}={v}" for k, v in env.items()))


if __name__ == "__main__":
    main()
