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

PAIR SKEW (owner 2026-10-23 clock gate): at TT and FF the same session measures the related launch/capture flop-pair
skew with CPPR credit over the reg->reg setup and hold path ends (tools/die_plan/pair_skew.tcl, run last: it zeroes the
clock uncertainties); rec["tt_pair_skew_ps"] / rec["ff_pair_skew_ps"] = worst |skew|, "<c>_pair_skew_p99_ps",
"<c>_pair_skew_pair" = [launch, capture], rec[<c>]["pair_skew"] per check.  textbook_lint.clock_rule_eval judges them.
"""
import argparse, json, os, re, subprocess, tempfile, sys
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"

# Shared physical clock tags: remove the actual source waveform phase,
# including generated bank phases, rather than guessing from data arrivals.
# Routes ship helpers flat under cl/; source-tree invocation uses common_flow.
_family_paths = (Path(__file__).resolve().with_name("clock_family.tcl"),
                 Path(__file__).resolve().parents[2] / "physical/common_flow/clock_family.tcl")
_family_path = next((p for p in _family_paths if p.is_file()), None)
if _family_path is None:
    raise FileNotFoundError("clock_family.tcl missing from source tree / shipped helper plan")
CLOCK_FAMILY_TCL = _family_path.read_text()
ACTIVE_TCL = CLOCK_FAMILY_TCL + r"""
proc ot_ck_arr {p clk} {
  set owners [get_property $p clocks]
  if {[llength $owners] != 1 || [ot_cf_root [get_full_name $owners]] ne [get_full_name $clk]} {
    error "CK_INSERTION: wrong/ambiguous clock ownership [get_full_name $p]"
  }
  return [ot_cf_wire $p $owners]
}
"""

# Same clock-source-port treatment as io_ref_routed.sdc. Routed SDCs can
# accidentally budget a second clock port as data against the first clock.
# Such a data arrival is not clock insertion and must not enter this record.
CLOCK_SETUP_TCL = r"""
set ot_ck_requested {CLOCK_REQUEST}
set ot_ck_selected [get_clocks -quiet $ot_ck_requested]
if {![llength $ot_ck_selected]} {
  set ot_ck_ports [list $ot_ck_requested]
  if {[regexp {^(.*)\[0\]$} $ot_ck_requested -> ot_ck_base]} {
    lappend ot_ck_ports $ot_ck_base
  } else {
    lappend ot_ck_ports [format {%s[0]} $ot_ck_requested]
  }
  foreach c [all_clocks] {
    foreach s [get_property $c sources] {
      set ot_ck_source [get_full_name $s]
      if {$ot_ck_source in $ot_ck_ports && [llength [get_ports -quiet $ot_ck_source]]} {
        lappend ot_ck_selected $c
      }
    }
  }
}
set ot_ck_selected [lsort -unique $ot_ck_selected]
if {[llength $ot_ck_selected] != 1} {
  error "CK_INSERTION: clock '$ot_ck_requested' must resolve to one clock, found [llength $ot_ck_selected]"
}
puts "OT_CK_SELECTED [get_full_name [lindex $ot_ck_selected 0]]"
foreach c [all_clocks] {
  foreach s [get_property $c sources] {
    set sn [get_full_name $s]
    if {![llength [get_ports -quiet $sn]]} continue
    foreach refclk [all_clocks] {
      unset_input_delay -clock $refclk [get_ports $sn]
      unset_input_delay -clock $refclk -clock_fall [get_ports $sn]
    }
    unset_input_delay [get_ports $sn]
    puts "OT_CK_CLOCK_PORT $sn: data input delays dropped"
  }
}
"""


# RAW-SOURCE (claude s81-grpA r4, 2026-10-14): the die delivers each tile clock pin at phi - R, R = this record's
# boundary mean (die clock delivery rule 10-13).  A kit whose SDC models that delivery with set_clock_latency -source
# -R_k per root (multi-root tiles: dsfd_vm_bgl28_mc5_h1pcs measured core -12.5 ps against a physical 402.8 ps) must
# not publish the COMPENSATED arrival as R: the die would deliver at phi and every sink would land R late.  --raw-source
# zeroes the source latency of every clock that has a source pin before measuring, so the record is the physical tree
# from the tile clock pin (what an ETM arc also excludes).  The closure loop's calibrate keeps the SDC's own reference
# (its CK_* drive the route IO SDC, which lives in the same compensated time base).
RAW_SOURCE_TCL = r"""
foreach c [all_clocks] {
  if {![llength [get_property $c sources]]} continue
  set_clock_latency -source 0 $c
  puts "OT_CK_RAW_SOURCE [get_full_name $c]"
}
"""


MACRO_CLOCK_SCOPE_TCL = r"""
proc ot_ck_macro_owned {p selected} {
  set owners {}
  foreach c [get_property $p clocks] { lappend owners [get_full_name $c] }
  set owners [lsort -unique $owners]
  # CLOCK-ROOT (ELEM-GAPS/HBMN2 2026-10-18, hfd_ckgen): the unclocked reference input of a macro that is itself a clock
  # SOURCE (the PLL refclk: the SDC creates the domain clocks on the PLL OUTPUT pins) is no sink of any measured clock --
  # skipped and recorded.  Any other unclocked macro clock pin stays an error.
  if {![llength $owners]} {
    set ot_mc_inst [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[catch {all_clocks} ot_mc_all]} { set ot_mc_all {} }
    foreach c $ot_mc_all { foreach s [get_property $c sources] {
      if {[string first "$ot_mc_inst/" [get_full_name $s]] == 0} { puts "OT_MC_UNCLOCKED [get_full_name $p] (clock source [get_full_name $s])"; return 0 }
    } }
  }
  if {[llength $owners] != 1} {
    error "CK_INSERTION: macro clock pin '[get_full_name $p]' requires one timing clock, found $owners"
  }
  puts "OT_MC_SOURCE [get_full_name $p] [lindex $owners 0]"
  # QW-CTLM5 10-19: a hard child's RAW clock entry (landed_raw: e.g. h16c ck_pm0/ck_pm1, the leaf's SRAM clock pins that
  # its ETM exports with NO timing arcs at all -- no clock-to-Q, no setup/hold check) has no active edge to measure, so
  # ot_cf_active (609270c0a) aborted the whole measurement on it (qfd_tt_ctlm_dv_safe3/4: 'missing unique active clock
  # edge u_hr/ck_pm0', no GATE_CK_DOMAIN, clock_rule coverage FAIL).  Such a pin is judged by the landed body
  # (OT_LANDED RAW_PIN: co-timed with its CTS-root pin per the leaf's closed record, fail-closed post-CTS), not here:
  # recorded and skipped.  A pin with ANY arc, or a non-block cell, still goes through ot_cf_active (fails closed).
  set ot_mc_master NULL
  if {[llength [info commands ord::get_db]]} {
    set ot_mc_master [[ord::get_db] findMaster [get_property [get_cells -of_objects $p] ref_name]]
  }
  if {$ot_mc_master ne "NULL" && [$ot_mc_master isBlock]} {
    sta::redirect_string_begin
    set ot_mc_failed [catch {report_edges -from $p} ot_mc_msg]
    set ot_mc_rep [sta::redirect_string_end]
    if {!$ot_mc_failed && ![regexp {\s[\^v]\s+->} $ot_mc_rep]} {
      puts "OT_MC_RAW_NOARC [get_full_name $p] [lindex $owners 0]"
      return 0
    }
  }
  set owner [lindex $owners 0]
  if {[info exists ::ot_cf_master] && [dict size $::ot_cf_master]} {set owner [ot_cf_root $owner]}
  return [expr {$owner eq [get_full_name $selected]}]
}
"""


# Boundary membership is physical connectivity, including disabled/false-path
# arcs. Timing-path enumeration omits precisely the paths an exception hides.
# OpenSTA includes asynchronous controls in -data_pins, so remove those before
# intersecting the structural input fanout with the selected clock's registers.
BOUNDARY_TCL = r"""
set bnd {}
set ot_ck_data {}
set ot_ck_async {}
foreach p [all_registers -async_pins] { dict set ot_ck_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] {
  set n [get_full_name $p]
  if {![dict exists $ot_ck_async $n]} { dict set ot_ck_data $n 1 }
}
set din [all_inputs -no_clocks]
if {[llength $din]} {
  foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $ot_ck_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
}
set dout [all_outputs]
if {[llength $dout]} {
  foreach p [get_fanin -to $dout -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
}
"""


# SPINE RC-CAL (S81-ELEM2-XFV 10-21): a clock_spine.tcl tree is balanced on the RCX-calibrated clock wire RC
# (ot_rc_cal_apply spine, OT_SPINE_RC_CAL default 1) and the hold flow times it on that RC too; measuring its CTS odb on
# setRC.tcl's platform clock RC (C 0.145 vs 0.10 fF/um) inflated a wire-dominated spine's pin-flop spread by ~45%
# (s81sl_vp8 r8: platform 125.0/112.6 ps TT/FF vs calibrated 77.5/69.9; FB 120.4/121.5 vs 71.7/57.7).  So the placement
# measurement of a spine-clocked odb uses the same calibrated clock RC (same env as tools/orfs_hold_mm.tcl:
# OT_RC_CAL=0 disables, OT_RC_CAL_R / OT_RC_CAL_C override).  TritonCTS trees and routed (SPEF) reads are unchanged.
_RCC_ON = os.environ.get("OT_RC_CAL", "1") != "0"
_RCC_R = os.environ.get("OT_RC_CAL_R", "1.40E-02")
_RCC_C = os.environ.get("OT_RC_CAL_C", "1.05E-01")
# PAIR SKEW (owner 2026-10-23 clock gate): related launch/capture flop-pair skew with CPPR credit, worst |.| over the
# reg->reg setup + hold path ends at TT and FF (tools/die_plan/pair_skew.tcl; shipped flat beside this file in routes,
# read from tools/die_plan in the source tree).  Without the helper the record says so and the gate WARNs.
_ps_paths = (Path(__file__).resolve().with_name("pair_skew.tcl"),
             Path(__file__).resolve().parents[1] / "die_plan/pair_skew.tcl")
_ps_path = next((p for p in _ps_paths if p.is_file()), None)
PAIR_SKEW_TCL = ("set ::ot_ps_lib_only 1\n" + _ps_path.read_text() + r"""
ot_ps_zero_unc
foreach ot_ps_d {max min} {
  set ot_ps_s [ot_ps_summary [ot_ps_pairs $ot_ps_d [expr {[info exists ::env(OT_PS_MAX_PATHS)] ? $::env(OT_PS_MAX_PATHS) : 200000}]]]
  puts "OT_PS_SUM\t$ot_ps_d\t[join $ot_ps_s \t]"
}
""") if _ps_path else ""


def pair_skew_record(out):
    """{"setup"|"hold": {n, worst_abs_ps, worst_signed_ps, p99_abs_ps, launch, capture}} from OT_PS_SUM lines"""
    res = {}
    for m in re.finditer(r"^OT_PS_SUM\t(max|min)\t(\d+)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t\n]*)$", out, re.M):
        if int(m[2]) == 0:
            continue
        res["setup" if m[1] == "max" else "hold"] = dict(n=int(m[2]), worst_abs_ps=float(m[3]),
                                                         worst_signed_ps=float(m[4]), p99_abs_ps=float(m[5]),
                                                         launch=m[6], capture=m[7])
    return res


SPINE_RC_CAL_TCL = (r"""set ot_ck_sp 0
foreach ot_ck_i [[ord::get_db_block] getInsts] { if {[string match clkbuf_sp_* [$ot_ck_i getName]]} { set ot_ck_sp 1; break } }
if {$ot_ck_sp} { set_wire_rc -clock -resistance %s -capacitance %s; puts "OT_CK_RC_CAL spine clock wire R %s C %s" }
""" % (_RCC_R, _RCC_C, _RCC_R, _RCC_C)) if _RCC_ON else ""


def tcl(corner, db, sdc, routed, clock, mlibs=(), raw_source=False):
    C = corner.upper()
    ml = "\n".join(f"read_liberty {l}" for l in mlibs)
    par = "read_spef /base/6_final.spef" if routed else f"source {PLAT}/setRC.tcl\n{SPINE_RC_CAL_TCL}estimate_parasitics -placement"
    return f"""
foreach l [glob {PLAT}/lib/NLDM/*RVT_{C}*] {{ read_liberty $l }}
foreach l [glob {PLAT}/lib/NLDM/*_LVT_{C}_* {PLAT}/lib/NLDM/*_SLVT_{C}_*] {{ if {{![string match *FAKE* $l]}} {{ read_liberty $l }} }}
{ml}
read_db /base/{db}
read_sdc /base/{sdc}
{par}
set_propagated_clock [all_clocks]
{RAW_SOURCE_TCL if raw_source else ''}
{CLOCK_SETUP_TCL.replace('CLOCK_REQUEST', clock)}
{CLOCK_FAMILY_TCL}
ot_cf_refresh
lassign [ot_cf_pins $ot_ck_selected] ot_ck_family_pins ot_ck_family_owners
set ot_ck_family_counts {{}}
dict for {{pin owner}} $ot_ck_family_owners {{dict incr ot_ck_family_counts [get_full_name $owner]}}
dict for {{owner count}} $ot_ck_family_counts {{puts "OT_CK_FAMILY $owner $count"}}
set regs {{}}
foreach p $ot_ck_family_pins {{ set n [get_full_name $p]; dict set regs [regsub {{/[^/]+$}} $n {{}}] $n }}
{BOUNDARY_TCL}
{ACTIVE_TCL}
{MACRO_CLOCK_SCOPE_TCL}
set ot_ck_clk [lindex $ot_ck_selected 0]
dict for {{i cp}} $regs {{
  set a [ot_ck_arr [get_pins $cp] $ot_ck_clk]
  if {{$a eq "" || $a eq "INF" || $a eq "-INF"}} continue
  set ot_ck_m ""
  set ot_ck_c [get_cells -quiet -of_objects [get_pins $cp]]
  if {{[llength $ot_ck_c]}} {{ set ot_ck_dm [[ord::get_db] findMaster [get_property $ot_ck_c ref_name]]; if {{$ot_ck_dm ne "NULL" && [$ot_ck_dm isBlock]}} {{ set ot_ck_m [$ot_ck_dm getName] }} }}
  puts "OT_CK [expr {{[dict exists $bnd $i] ? 1 : 0}}] $a $ot_ck_m"
}}
foreach inst [[ord::get_db_block] getInsts] {{
  if {{![[$inst getMaster] isBlock]}} continue
  foreach it [$inst getITerms] {{
    set n [$it getNet]
    if {{$n eq "NULL" || $n eq ""}} continue
    if {{[[$it getMTerm] getSigType] ne "CLOCK" && [$n getSigType] ne "CLOCK"}} continue
    set p [get_pins -quiet "[$inst getName]/[[$it getMTerm] getName]"]
    if {{[llength $p] != 1}} {{ error "CK_INSERTION: unresolved macro clock pin [$inst getName]/[[$it getMTerm] getName]" }}
    if {{![ot_ck_macro_owned $p $ot_ck_clk]}} continue
    set a [ot_ck_arr $p $ot_ck_clk]
    set sl [get_property $p slew_max_rise]
    if {{![string is double -strict $a] || ![string is double -strict $sl]}} {{ error "CK_INSERTION: missing macro clock arrival/slew [get_full_name $p]" }}
    puts "OT_MC [get_full_name $p] $a $sl [$n getName]"
  }}
}}
{PAIR_SKEW_TCL if corner.lower() in ("tt", "ff") else ""}
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


CTP_RE = re.compile(r"timing_type\s*:\s*max_clock_tree_path\s*;.*?values\(\"([\d.]+)\"\).*?values\(\"([\d.]+)\"\)", re.S)


def child_refs(root, mlibs, corner):
    """CHILD-FLOP (SM-RP4 2026-10-18, owner 0dq "child-flop spread for a cluster"): {block master: (R ps, basis)} at this
    corner for every hard child whose liberty the route reads.  R = the child's routed boundary-register insertion
    (views/<child>/insertion.json <corner>.boundary.mean, the reference its pin flops launch / capture at), else the
    lib's max_clock_tree_path.  A hard child's clock pin is a register to all_registers (its ETM carries the setup /
    hold checks), so its RAW pin arrival -- placed EARLY by the spine by exactly this R -- is not a flop arrival."""
    out = {}
    for lib in mlibs:
        host = Path(root) / lib[len("/src/"):]
        name = re.sub(rf"_{corner}\.lib$", "", host.name)
        ij = host.parent / "insertion.json"
        try:
            b = ((json.loads(ij.read_text()).get(corner) or {}).get("boundary") or {}) if ij.is_file() else {}
        except (OSError, ValueError):
            b = {}
        if b.get("n") and b.get("mean") is not None:
            out[name] = (float(b["mean"]), "insertion.json boundary mean")
            continue
        try:
            vals = [float(x) for m in CTP_RE.finditer(host.read_text(errors="replace")) for x in m.groups()]
        except OSError:
            vals = []
        if vals:
            out[name] = (max(vals), "lib max_clock_tree_path")
    return out


def pin_sourced_clocks(sdc_text):
    """CLOCK-ROOT (ELEM-GAPS/HBMN2 2026-10-18, hfd_ckgen): a clock-root view (PLL hard core) creates its domain clocks on
    the PLL OUTPUT pins and forwards each to an output port as a divide_by 1 generated clock.  Its measured clock is the
    pin clock; the Liberty pin it maps to is the forwarded port.  [(master clock name, port)] for each such pair; a pin
    clock forwarded to no port, or to several, is not mapped (no record rather than a guessed one)."""
    pins = {m[1]: m[0] for m in re.findall(r"^create_clock\s+-name\s+(\S+)[^\n]*\[get_pins\s+\{([^}]+)\}\]", sdc_text, re.M)}
    fwd = {}
    for m in re.finditer(r"^create_generated_clock\s+[^\n]*-source\s+\[get_pins\s+\{([^}]+)\}\][^\n]*-divide_by\s+1\b[^\n]*"
                         r"\[get_ports\s+\{([^}]+)\}\]\s*$", sdc_text, re.M):
        if m[1] in pins:
            fwd.setdefault(pins[m[1]], []).append(m[2])
    return [(name, ports[0]) for name, ports in fwd.items() if len(ports) == 1]


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
    ap.add_argument("--all-clocks", action="store_true", help="measure each external clock in the selected write_sdc, preserving per-pin references")
    ap.add_argument("--route-corner", default="", help="TC/TT: CK_SS_* carry the TT insertion (route-time IO reference)")
    ap.add_argument("--raw-source", action="store_true",
                    help="zero every clock's source latency before measuring: the physical insertion R from the tile clock "
                         "pin that the die compensates (view export, pre-route gate); never the loop calibrate")
    a = ap.parse_args()
    base = a.base.resolve()
    if a.all_clocks:
        sdc = "6_final.sdc" if a.routed else next((s for s in ("4_cts.sdc", "3_place.sdc", "2_floorplan.sdc", "1_synth.sdc") if (base / s).exists()), None)
        if sdc is None:
            raise SystemExit(f"no CTS SDC under {base}")
        stext = (base / sdc).read_text()
        clocks = re.findall(r"^create_clock\s+-name\s+(\S+)[^\n]*\[get_ports\s+\{([^}]+)\}\]", stext, re.M)
        clocks += pin_sourced_clocks(stext)
        if not clocks or any(len(pin.split()) != 1 for name, pin in clocks):
            raise SystemExit("write_sdc must identify each external clock's single source port")
        if len({pin for name, pin in clocks}) != len(clocks):
            raise SystemExit("multiple external clocks on one pin: select their references explicitly")
        pin_src = {m[0]: m[1] for m in re.findall(r"^create_clock\s+-name\s+(\S+)[^\n]*\[get_pins\s+\{([^}]+)\}\]", stext, re.M)}
        records = {}
        with tempfile.TemporaryDirectory() as td:
            for index, (name, pin) in enumerate(clocks):
                out = Path(td) / f"clock_{index}.json"
                cmd = [sys.executable, str(Path(__file__).resolve()), "--base", str(base), "--clock", name,
                       "--image", a.image, "--route-corner", a.route_corner, "--output", str(out)]
                if a.routed:
                    cmd.append("--routed")
                if a.raw_source:
                    cmd.append("--raw-source")
                subprocess.run(cmd, check=True)
                rec = json.loads(out.read_text())
                rec["lib_clock_pin"] = pin
                rec["clock_mapping_basis"] = (f"{sdc} create_clock -name {name} [get_ports {{{pin}}}]" if name not in pin_src
                                              else f"{sdc} create_clock -name {name} [get_pins {{{pin_src[name]}}}] -> "
                                                   f"create_generated_clock -divide_by 1 [get_ports {{{pin}}}] (clock root)")
                records[pin] = rec
        rec = dict(next(iter(records.values())))
        rec["clock_measurements"] = records
        rec["raw_source"] = bool(a.raw_source)
        a.output.write_text(json.dumps(rec, indent=1) + "\n")
        return
    if a.routed:
        db, sdc = "6_final.odb", "6_final.sdc"
    else:
        db = "4_1_cts.odb"
        sdc = next((s for s in ("4_cts.sdc", "3_place.sdc", "2_floorplan.sdc", "1_synth.sdc") if (base / s).exists()), None)
        if not (base / db).exists() or not sdc:
            raise SystemExit(f"no {db} / SDC under {base}")
    rec = dict(schema="opentallas.closure_loop.ck_insertion.v1", base=str(base), db=db, sdc=sdc, clock=a.clock,
               parasitics="spef" if a.routed else "placement-estimated", raw_source=bool(a.raw_source))
    env = {}
    need_tt = a.route_corner.upper() in ("TC", "TT")
    for corner in ("ss", "tt", "ff"):
        sroot, mlibs = macro_libs(base, corner)
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "s.tcl").write_text(tcl(corner, db, sdc, a.routed, a.clock, mlibs, a.raw_source))
            mnt = ["-v", f"{sroot}:/src:ro"] if sroot else []
            result = subprocess.run(["docker", "run", "--rm", "-v", f"{base}:/base:ro", "-v", f"{td}:/t:ro", *mnt, a.image,
                                  "bash", "-lc",
                                  "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl"],
                                 capture_output=True, text=True)
            out = result.stdout
            if result.returncode:
                raise SystemExit(f"{corner}: clock insertion replay failed ({result.returncode})\n{out[-1500:]}\n{result.stderr[-1500:]}")
        b, al, cb, cal, craw, sb, sal = [], [], [], [], {}, [], []
        refs = child_refs(sroot, mlibs, corner) if sroot else {}
        for m in re.finditer(r"^OT_CK (\d) (\S+)(?: (\S+))?[ \t]*$", out, re.M):
            x = float(m[2])
            al.append(x)
            if m[1] == "1":
                b.append(x)
            if m[3]:                         # a hard child's clock pin: its flops sit R later (unknown R: kept raw)
                r = refs.get(m[3])
                craw.setdefault(m[3], [r[1] if r else "no reference: raw pin arrival", r[0] if r else 0.0, 0])[2] += 1
                x = x + (r[0] if r else 0.0)
            else:                            # a soft (glue) register of this root
                sal.append(x)
                if m[1] == "1":
                    sb.append(x)
            cal.append(x)
            if m[1] == "1":
                cb.append(x)
        mrows = [(m[1], float(m[2]), float(m[3]), m[4])
                 for m in re.finditer(r"^OT_MC (\S+) (\S+) (\S+) (\S+)", out, re.M)]
        rec[corner] = dict(clock_family={name: int(n) for name, n in re.findall(r"^OT_CK_FAMILY (\S+) (\d+)$", out, re.M)},
                           boundary=stats(b), all=stats(al), errors=re.findall(r"\[ERROR[^\n]*", out)[:5],
                           macros=macro_summary(mrows, round(sum(al) / len(al), 1) if al else None),
                           macro_libs=len(mlibs))
        if corner in ("tt", "ff"):
            ps = pair_skew_record(out)
            rec[corner]["pair_skew"] = ps or ("not measured: pair_skew.tcl not shipped" if not PAIR_SKEW_TCL else
                                              "no reg->reg path ends")
            if ps:
                w = max(ps.values(), key=lambda x: x["worst_abs_ps"])
                rec[f"{corner}_pair_skew_ps"] = w["worst_abs_ps"]
                rec[f"{corner}_pair_skew_p99_ps"] = max(x["p99_abs_ps"] for x in ps.values())
                rec[f"{corner}_pair_skew_pair"] = [w["launch"], w["capture"]]
        if craw:
            rec[corner]["child_flop"] = dict(boundary=stats(cb), all=stats(cal),
                                             refs={k: dict(basis=v[0], ref_ps=round(v[1], 1), pins=v[2])
                                                   for k, v in sorted(craw.items())},
                                             soft=dict(boundary=stats(sb), all=stats(sal)))   # PL-GATE: per-root glue
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
