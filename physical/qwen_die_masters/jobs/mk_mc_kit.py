#!/usr/bin/env python3
"""Write a multi-clock die-master kit (physical/qwen_die_masters/mc/<master>/plain.sdc, io_plain.sdc, io_ref_skew.sdc,
repair_budget.tcl) and its 833.333 ps sign-off SDC (signoff/<master>.sdc) from a domain table:
python3 mk_mc_kit.py MASTER 'clk:in1 in2[*]:out1 out2[*]' ... [--skew-intra name1,name2]
Every domain pair is an unrelated-clock crossing (max delay one period - 60 ps, min 0, ignoring latency).  Ports use
150 ps (die wire to another region) unless their domain is listed in --intra (90 ps)."""
import argparse
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("master")
ap.add_argument("domains", nargs="+")
ap.add_argument("--intra", default="")
ap.add_argument("--false", default="rst_n")
a = ap.parse_args()
dom = {}
for d in a.domains:
    c, i, o = d.split(":")
    dom[c] = (i.split(), o.split())
intra = set(x for x in a.intra.split(",") if x)
clk_port = lambda c: c.replace("<", "[").replace(">", "]")


def clocks(T):
    return [f"create_clock -name {c} -period {T} [get_ports {{{clk_port(c)}}}]" for c in dom] + \
           ["set_clock_uncertainty -setup 60 [all_clocks]", "set_clock_uncertainty -hold 25 [all_clocks]"]


def cross(T):
    o = ["# unrelated-clock crossings: one period minus the setup uncertainty, both directions; hold: non-negative"]
    for x in dom:
        for y in dom:
            if x != y:
                o += [f"set_max_delay -ignore_clock_latency {T - 60:.3f} -from [get_clocks {x}] -to [get_clocks {y}]",
                      f"set_min_delay -ignore_clock_latency 0 -from [get_clocks {x}] -to [get_clocks {y}]"]
    return o


def plainio():
    o = []
    for c, (i, q) in dom.items():
        if i: o.append(f"set_input_delay 166.667 -clock {c} [get_ports {{{' '.join(i)}}}]")
        if q: o.append(f"set_output_delay 166.667 -clock {c} [get_ports {{{' '.join(q)}}}]")
    return o + [f"set_false_path -from [get_ports {{{a.false}}}]"]


ref = ["# die-context boundary per domain, referenced to the propagated arrival L at a register of that domain's tree:",
       "# 0.2 T outside + 150 ps (die wire to another region; 90 ps for the --intra domains), hold allowance 50 ps",
       "set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]",
       "sta::worst_slack_cmd max", "unset_input_delay [all_inputs]", "unset_output_delay [all_outputs]",
       "foreach {clk sk ins outs} {"]
for c, (i, q) in dom.items():
    ref.append(f"  {c} {90 if c in intra else 150} {{{' '.join(i)}}} {{{' '.join(q)}}}")
ref += ["} {",
        "  set ref {}",
        "  if {[llength $ins]} { set ref [ot_pf_ref [get_ports $ins]] }",
        "  if {![llength $ref]} { set ref [lindex [all_registers -clock $clk -clock_pins] 0] }",
        "  set lmax [get_property $ref arrival_max_rise]; set lmin [get_property $ref arrival_min_rise]",
        "  set T [get_property [get_clocks $clk] period]",
        "  puts \"QDM $clk ref [get_full_name $ref] L max $lmax min $lmin skew $sk\"",
        "  if {[llength $ins]} {",
        "    set_input_delay  [expr {0.2*$T + $lmax + $sk}] -max -clock $clk [get_ports $ins]",
        "    set_input_delay  [expr {$lmin - ([info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0)}]       -min -clock $clk [get_ports $ins] }",
        "  if {[llength $outs]} {",
        "    set_output_delay [expr {0.2*$T - $lmax + $sk}] -max -clock $clk [get_ports $outs]",
        "    set_output_delay [expr {-$lmin - $ot_hk}]      -min -clock $clk [get_ports $outs] }",
        "}", f"set_false_path -from [get_ports {{{a.false}}}]"]
# sign-off keeps the original reference (route-time PINFLOP only): the verdict re-times at the routed insertion anyway
_new = ["  set ref {}", "  if {[llength $ins]} { set ref [ot_pf_ref [get_ports $ins]] }",
        "  if {![llength $ref]} { set ref [lindex [all_registers -clock $clk -clock_pins] 0] }"]
_k = ref.index(_new[0])
ref_so = ref[:_k] + ["  set ref [lindex [all_registers -clock $clk -clock_pins] 0]"] + ref[_k + 3:]
K = D / "mc" / a.master
K.mkdir(parents=True, exist_ok=True)
shutil.copy(D / "repair_budget.tcl", K / "repair_budget.tcl")
(K / "plain.sdc").write_text("\n".join([f"# {a.master}: multi-clock kit (jobs/mk_mc_kit.py); route over-constrained at 770 ps"]
                                       + clocks(770) + cross(770) + plainio() +
                                       ["set_max_fanout 32 [current_design]", "# die-wire context (r21 die STA): one <= 430.56 um hop + receiver pin", "set_load 80 [all_outputs]", "set_input_transition 150 [all_inputs -no_clocks]",
                                        "set_max_transition 260 [current_design]"]) + "\n")
(K / "io_plain.sdc").write_text("\n".join(["unset_input_delay [all_inputs]", "unset_output_delay [all_outputs]"] + plainio()) + "\n")
PF = (D / "pinflop_ref.tcl").read_text()   # route-time PINFLOP reference procs (drive-0849 2026-10-10); not in sign-off
_i = next(i for i, l in enumerate(ref) if not l.startswith("#"))
(K / "io_ref_skew.sdc").write_text("\n".join(ref[:_i] + [PF.rstrip("\n")] + ref[_i:]) + "\n")
(D / "signoff" / f"{a.master}.sdc").write_text("\n".join([f"# {a.master} sign-off at 833.333 ps (jobs/mk_mc_kit.py)"] + clocks(833.333)
                                                       + ["set_propagated_clock [all_clocks]"] + cross(833.333)
                                                       + ["set ::env(OT_IO_HOLD_SKEW) 50"] + ref_so) + "\n")
print(K)
