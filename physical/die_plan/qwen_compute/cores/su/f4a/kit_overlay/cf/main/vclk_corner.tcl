# GENERATED-COPY of tools/die_plan/vclk_corner.tcl (FLOW 2026-10-25; METHODOLOGY ruling 9.7, BRIEFING decision 5e).
# The kit IO virtual clock stands for the neighbour's face flop, whose insertion tracks the corner.  constraint.sdc
# carries the bound TT insertion (setup basis); FF-only steps (run_kit.sh FF GRT hold repair, hold_gate.tcl, sign-off
# FF) switch the vclk source latency to the bound FF insertion.  One SDC cannot carry both: OpenSTA's -min / -max
# source latency are early / late, not hold / setup analysis.
# Env: OT_VCLK_TT, OT_VCLK_FF (SDC time units; config.mk exports), OT_VCLK_CORNER = tt | ff (bind on source).
proc ot_vclk_bind {corner} {
  set k [expr {$corner eq "ff" ? "OT_VCLK_FF" : "OT_VCLK_TT"}]
  if {![info exists ::env($k)] || ![string is double -strict $::env($k)]} { error "vclk_corner: $k unset or not a number" }
  set vc {}
  foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend vc $c } }
  if {[llength $vc] != 1} { error "vclk_corner: expected exactly one IO virtual clock, found [llength $vc]" }
  set_clock_latency -source $::env($k) [lindex $vc 0]
  puts "OT_VCLK_BIND corner $corner clock [get_full_name [lindex $vc 0]] source_latency $::env($k)"
}
if {[info exists ::env(OT_VCLK_CORNER)] && $::env(OT_VCLK_CORNER) ne ""} { ot_vclk_bind $::env(OT_VCLK_CORNER) }
