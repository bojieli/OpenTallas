#!/usr/bin/env python3
"""wires_only_ioref.py CLUSTER_SPEC.json OUT.sdc -- die-context IO reference of a WIRES-ONLY cluster (2026-10-13, qdq q8).

A cluster whose top has no flop of its own keeps every boundary register INSIDE a hard child.  The generic boundary
(physical/qwen_die_masters/io_ref_skew.sdc) then finds no pin flop and falls back to the first child clock PIN, whose
arrival lacks the child's own clock insertion (its lib carries it in the check / launch arcs and in *_clock_tree_path):
the reference L sits one child insertion (~200 ps) early, so every cluster input fails hold by about that much (q7: wrr ->
lane-pair pins -54..-78 ps on 2,056 ports) and every output loses it from its setup budget.

The generated file re-applies the SAME formulas with L = median over the children of (clock-pin arrival + that child's
insertion from its TT lib; max for L_max, min for L_min -- the numbers the kit's spine balances to).  It is listed in the
cluster spec twice: "sdc_extra" (inlined at the end of clock.sdc and signoff.sdc: acts only once the clock is propagated)
and "boundary_tcl" (route hooks: wraps clock_tree_synthesis in pre_cts.tcl, applies in pre_grt.tcl, nothing in
post_drt.tcl, which must leave the plain boundary).  Re-run whenever a child view changes (the insertions are literals).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/hier_contract"))
import child_lint  # noqa: E402

BODY = r"""
# "clock": "entries" clusters (one clock port per child clock pin): the die delivers phi - R_i at entry i, R_i = entry
# wire + the child's routed boundary insertion.  Modelled as a per-port SOURCE latency Lref - R_i (Lref = the largest
# R_i), so every child's boundary registers sit at Lref and the hops between children carry no insertion difference.
# The entry wire is measured with the latencies cleared first (each SDC mode / scene carries its own).
proc ot_wc_entries {} {
  foreach src [get_property [get_clocks core_clk] sources] { set_clock_latency -source 0.0 -clock [get_clocks core_clk] $src }
  catch {sta::worst_slack_cmd max}
  set rows {}
  foreach c [get_cells -quiet -hierarchical *] {
    set m [get_property $c ref_name]
    if {![dict exists $::ot_wc_ins $m]} { continue }
    lassign [dict get $::ot_wc_ins $m] port imin imax imean
    set p [get_pins -quiet "[get_full_name $c]/$port"]
    if {![llength $p]} { continue }
    set a [get_property $p arrival_max_rise]
    if {![string is double -strict $a]} { continue }
    set tp {}
    catch {set tp [get_ports -quiet -of_objects [get_nets -quiet -of_objects $p]]}
    if {[llength $tp] != 1} { puts "OT_WC entries: [get_full_name $p] has no single clock port -- latency not set"; continue }
    lappend rows [list [get_full_name $tp] $tp [get_full_name $c] $a $imean]
  }
  if {![llength $rows]} { puts "OT_WC entries: no child clock arrival -- no entry latency"; return }
  set lref 0.0
  foreach r $rows { lassign $r tn tp cn w im; if {$w + $im > $lref} { set lref [expr {$w + $im}] } }
  foreach r $rows {
    lassign $r tn tp cn w im
    set lat [expr {$lref - $w - $im}]
    set_clock_latency -source $lat -clock [get_clocks core_clk] $tp
    puts [format "OT_WC entry %s -> %s wire %.1f ps + child R %.1f = R_i %.1f ps; die delivers phi - R_i (source latency %.1f)" $tn $cn $w $im [expr {$w + $im}] $lat]
  }
  puts [format "OT_WC entries: %d clock entries aligned at Lref %.1f ps" [llength $rows] $lref]
}
proc ot_wc_apply {} {
  set mx {}; set mn {}; set raw {}
  if {[info exists ::ot_wc_entry_mode] && $::ot_wc_entry_mode} { ot_wc_entries }
  # arrivals need an updated timing graph (as io_ref_skew.sdc ot_pf_ref): without it get_property arrival_* on a child pin
  # segfaults OpenSTA at the first read_sdc of a wires-only netlist (synth_odb, dscoll_ces0_sp gate 2026-10-13)
  catch {sta::worst_slack_cmd max}
  foreach c [get_cells -quiet -hierarchical *] {
    set m [get_property $c ref_name]
    if {![dict exists $::ot_wc_ins $m]} { continue }
    lassign [dict get $::ot_wc_ins $m] port imin imax
    set p [get_pins -quiet "[get_full_name $c]/$port"]
    if {![llength $p]} { continue }
    set a [get_property $p arrival_max_rise]; set b [get_property $p arrival_min_rise]
    if {![string is double -strict $a] || ![string is double -strict $b]} { continue }
    lappend mx [expr {$a + $imax}]; lappend mn [expr {$b + $imin}]; lappend raw $a
  }
  if {![llength $mx]} { puts "OT_WC ioref: no child clock arrival (clock not propagated?) -- boundary unchanged"; return }
  if {[lindex [lsort -real $raw] end] <= 0.0} { puts "OT_WC ioref: ideal clock -- plain boundary kept"; return }
  set lmax [lindex [lsort -real $mx] [expr {[llength $mx] / 2}]]
  set lmin [lindex [lsort -real $mn] [expr {[llength $mn] / 2}]]
  set sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  unset_input_delay [all_inputs]
  unset_output_delay [all_outputs]
  set_input_delay [expr {166.667 + $lmax + $sk}] -max -clock core_clk [all_inputs -no_clocks]
  set_input_delay [expr {$lmin - $hki}] -min -clock core_clk [all_inputs -no_clocks]
  set_output_delay [expr {166.667 - $lmax + $sk}] -max -clock core_clk [all_outputs]
  set_output_delay [expr {0 - $lmin - $hk}] -min -clock core_clk [all_outputs]
  puts "OT_WC ioref: [llength $mx] children, L max $lmax min $lmin (child pin arrival + child insertion; range [lindex [lsort -real $mx] 0] .. [lindex [lsort -real $mx] end])"
}
set ot_wc_stage apply
for {set ot_wc_f [info frame]} {$ot_wc_f > 0} {incr ot_wc_f -1} {
  set ot_wc_d [info frame $ot_wc_f]
  if {![dict exists $ot_wc_d file]} continue
  set ot_wc_t [file tail [dict get $ot_wc_d file]]
  if {[string match *pre_cts.tcl $ot_wc_t]} { set ot_wc_stage wrap; break }
  if {[string match *post_drt.tcl $ot_wc_t]} { set ot_wc_stage skip; break }
}
if {$ot_wc_stage eq "wrap"} {
  # pre_cts.tcl: the io_ref wrapper (pre_cts_skew.tcl) applies the generic boundary right after the tree is built; this
  # wrapper runs after it
  if {![llength [info commands ::ot_wc_cts_orig]]} {
    rename clock_tree_synthesis ::ot_wc_cts_orig
    proc clock_tree_synthesis {args} { ::ot_wc_cts_orig {*}$args; ot_wc_apply }
  }
} elseif {$ot_wc_stage eq "apply"} {
  ot_wc_apply
}
"""


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text())
    rows = []
    for ch in spec["children"]:
        v = ch["view"]
        m = Path(v).name
        if any(r[0] == m for r in rows):
            continue
        lib = ROOT / v / f"{m}_tt.lib"
        if not lib.exists():
            sys.exit(f"wires_only_ioref: {lib} missing (the child is not closed / its view not merged yet)")
        ins = {k: x for k, x in child_lint.clock_insertion(lib.read_text(errors="replace")).items() if x}
        if len(ins) != 1:
            sys.exit(f"wires_only_ioref: {m}: expected one clock pin with clock-tree arcs, got {sorted(ins)}")
        (port, x), = ins.items()
        lo, hi = x["min_ps"], x["max_ps"]
        mean = hi
        # spec "child_clock_ref": "boundary" (as ref_tile.py child_insertions): the children's ROUTED boundary registers
        # (insertion.json tt.boundary min / max) are the cluster's boundary registers
        ij = ROOT / v / "insertion.json"
        if spec.get("child_clock_ref") == "boundary" and ij.exists():
            b = json.loads(ij.read_text()).get("tt", {}).get("boundary", {})
            if b.get("n"):
                lo, hi = round(float(b["min"]), 1), round(float(b["max"]), 1)
                mean = round(float(b["mean"]), 1)
        rows.append((m, port, lo, hi, mean))
    head = (f"# GENERATED by tools/ref_tile/wires_only_ioref.py from {sys.argv[1]} (children's TT libs) -- do not edit;\n"
            "# re-run after any child view changes.  Wires-only cluster: the boundary registers are inside the hard children,\n"
            "# so the die-context reference is child clock-pin arrival + child insertion (see the generator's docstring).\n"
            "set ::ot_wc_ins [dict create " + " ".join(f"{m} {{{p} {lo} {hi} {mean}}}" for m, p, lo, hi, mean in rows) + "]\n"
            f"set ::ot_wc_entry_mode {1 if spec.get('clock') == 'entries' else 0}\n")
    Path(sys.argv[2]).write_text(head + BODY)
    print("wires_only_ioref:", "; ".join(f"{m} {p} {lo}..{hi} ps (R {mean})" for m, p, lo, hi, mean in rows),
          "; clock entries" if spec.get("clock") == "entries" else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
