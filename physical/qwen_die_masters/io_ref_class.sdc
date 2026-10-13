# CLOCK-CLASS for the in-route QDM boundary (el1013-smh-r14 2026-10-13).  Opt-in: env OT_IO_REF_CLASS=1 (read by
# pre_cts_skew.tcl / pre_ref_skew.tcl right after io_ref_skew.sdc; without it nothing changes).
#
# io_ref_skew.sdc references EVERY data port to one register clock arrival L (the median input pin flop).  A block with
# two clock classes on one port clock -- the SM tile cluster: the tile ICG's wake registers on the raw clock at ~4 ps,
# every other register behind the gate and a 1.19 ns spine -- then times its raw-class ports against the gated L:
# cgi -> u_cgt.en / wq at -816 ps (r13 post-CTS, 2 endpoints) and cgo's output min 1.1 ns away from its launch flop.
# The sign-off (physical/common_flow/io_ref_routed.sdc) and the link budget (link_budget_consistent.sdc) already split
# the classes; the route-time repair passes (CTS, GRT, DRT) chased the false pairing for minutes instead.
#
# Rule (the sign-off's): a port ALL of whose boundary registers (reached through <= 8 BUF / INV / HB cells) have a
# clock arrival more than
# OT_IOREF_CLASS_GAP (default the larger of 0.25 T and 150 ps) away from L is re-referenced to its own registers
# (an input: every register behind <= 3 gate levels; a hard child or deeper logic on the way leaves the port alone):
#     input  max = 166.667 + Lp_max + skew     min = Lp_min - in_hold_skew
#     output max = 166.667 - Lp_max + skew     min = -Lp_min - hold_skew
# This is not a false path: the port keeps its full 0.2 T / hold contract, against the clock that really launches or
# captures it (die context: cgo of one tile drives cgi of the next, raw class to raw class).  A port that reaches
# registers of both classes is left on L and reported: that is a structural finding, not a reference question.
if {[info exists qdm_lmax] && [info exists qdm_lmin] && [string is double -strict $qdm_lmax]} {
  proc ot_qc_isbuf {c} { return [regexp {^(BUF|HB|INV)} [get_property $c ref_name]] }
  # clock pins of the registers an input port reaches: through BUF / INV / HB chains, and through ONE gate level
  proc ot_qc_in {port} {
    set out {}; set seen [dict create]
    set work [list [list [get_nets -quiet [get_full_name $port]] 0 0]]
    while {[llength $work]} {
      lassign [lindex $work 0] nets hop gate; set work [lrange $work 1 end]
      foreach n $nets {
        foreach pin [get_pins -quiet -of_objects $n] {
          if {[string first / [get_full_name $pin]] < 0 || [get_property $pin direction] ne "input"} continue
          set c [get_cells -quiet -of_objects $pin]; if {![llength $c]} continue
          set fn [get_full_name $c]
          set ck [get_pins -quiet "$fn/CLK"]
          if {[llength $ck]} { if {![dict exists $seen $fn]} { dict set seen $fn 1; lappend out $ck }; continue }
          set ism 0; catch {set ism [[[sta::sta_to_db_inst $c] getMaster] isBlock]}
          if {$ism} { return {} }
          set isb [ot_qc_isbuf $c]
          if {$hop >= 8 || (!$isb && $gate >= 3)} { return {} }
          set next {}
          foreach op [get_pins -quiet -of_objects $c] { if {[get_property $op direction] eq "output"} { lappend next [get_nets -quiet -of_objects $op] } }
          lappend work [list $next [expr {$hop + 1}] [expr {$gate + ($isb ? 0 : 1)}]]
        }
      }
    }
    return $out
  }
  # clock pin of the register that launches an output port (through BUF / INV / HB only)
  proc ot_qc_out {port} {
    set n [get_nets -quiet [get_full_name $port]]
    for {set hop 0} {$hop < 8 && [llength $n]} {incr hop} {
      set drv {}
      foreach pin [get_pins -quiet -of_objects $n] { if {[string first / [get_full_name $pin]] >= 0 && [get_property $pin direction] eq "output"} { lappend drv $pin } }
      if {[llength $drv] != 1} { return {} }
      set c [get_cells -quiet -of_objects [lindex $drv 0]]
      set fn [get_full_name $c]
      set ck [get_pins -quiet "$fn/CLK"]
      if {[llength $ck]} { return $ck }
      if {![ot_qc_isbuf $c]} { return {} }
      set n {}
      foreach ip [get_pins -quiet -of_objects $c] { if {[get_property $ip direction] eq "input"} { set n [get_nets -quiet -of_objects $ip] } }
    }
    return {}
  }
  proc ot_qc_arr {cks} {
    set lo ""; set hi ""
    foreach ck $cks {
      set a [get_property $ck arrival_max_rise]; set b [get_property $ck arrival_min_rise]
      if {![string is double -strict $a] || ![string is double -strict $b]} { return {} }
      if {$hi eq "" || $a > $hi} { set hi $a }
      if {$lo eq "" || $b < $lo} { set lo $b }
    }
    if {$hi eq ""} { return {} }
    return [list $lo $hi]
  }
  set ot_qc_T [get_property [get_clocks core_clk] period]
  set ot_qc_gap [expr {[info exists ::env(OT_IOREF_CLASS_GAP)] && $::env(OT_IOREF_CLASS_GAP) ne "" ? $::env(OT_IOREF_CLASS_GAP) : max(0.25 * $ot_qc_T, 150.0)}]
  set ot_qc_sk [expr {[info exists ot_sk] ? $ot_sk : 90}]
  set ot_qc_hk [expr {[info exists ot_hk] ? $ot_hk : 50}]
  set ot_qc_hki [expr {[info exists ot_hki] ? $ot_hki : 0}]
  set ot_qc_ni 0; set ot_qc_no 0; set ot_qc_mix {}
  catch {sta::worst_slack_cmd max}
  foreach p [all_inputs -no_clocks] {
    set cks [ot_qc_in $p]; if {![llength $cks]} continue
    set far 0; set near 0
    foreach ck $cks { set a [get_property $ck arrival_max_rise]; if {[string is double -strict $a] && abs($a - $qdm_lmax) > $ot_qc_gap} { incr far } else { incr near } }
    if {!$far} continue
    if {$near} { lappend ot_qc_mix [get_full_name $p]; continue }
    set lh [ot_qc_arr $cks]; if {![llength $lh]} continue
    lassign $lh lo hi
    set_input_delay [expr {166.667 + $hi + $ot_qc_sk}] -max -clock core_clk $p
    set_input_delay [expr {$lo - $ot_qc_hki}] -min -clock core_clk $p
    puts [format "QDM CLASS input %s re-referenced to its own registers (%d): clock arrival %.1f..%.1f (block reference %.1f)" [get_full_name $p] [llength $cks] $lo $hi $qdm_lmax]
    incr ot_qc_ni
  }
  foreach p [all_outputs] {
    set ck [ot_qc_out $p]; if {![llength $ck]} continue
    set a [get_property $ck arrival_max_rise]
    if {![string is double -strict $a] || abs($a - $qdm_lmax) <= $ot_qc_gap} continue
    set lh [ot_qc_arr $ck]; if {![llength $lh]} continue
    lassign $lh lo hi
    set_output_delay [expr {166.667 - $hi + $ot_qc_sk}] -max -clock core_clk $p
    set_output_delay [expr {0 - $lo - $ot_qc_hk}] -min -clock core_clk $p
    puts [format "QDM CLASS output %s re-referenced to its launch register: clock arrival %.1f..%.1f (block reference %.1f)" [get_full_name $p] $lo $hi $qdm_lmax]
    incr ot_qc_no
  }
  if {[llength $ot_qc_mix]} { puts "QDM CLASS mixed-class ports left on the block reference ([llength $ot_qc_mix]): [lrange $ot_qc_mix 0 7]" }
  puts "QDM CLASS gap $ot_qc_gap: $ot_qc_ni inputs / $ot_qc_no outputs re-referenced"
} else {
  puts "QDM CLASS skipped: no QDM reference in this session"
}
