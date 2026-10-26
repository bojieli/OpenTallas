# GENERATED-COPY of tools/die_plan/vclk_corner.tcl (FLOW 2026-10-25; METHODOLOGY ruling 9.7, BRIEFING decision 5e).
# The kit IO virtual clock stands for the neighbour's face flop, whose insertion tracks the corner.  constraint.sdc
# carries the bound TT insertion (setup basis); FF-only steps (run_kit.sh FF GRT hold repair, hold_gate.tcl, sign-off
# FF) switch the vclk source latency to the bound FF insertion.  One SDC cannot carry both: OpenSTA's -min / -max
# source latency are early / late, not hold / setup analysis.
# Env: OT_VCLK_TT, OT_VCLK_FF (SDC time units; config.mk exports), OT_VCLK_CORNER = tt | ff (bind on source).
# A marked generated kit has a separate FF source-latency overlay for hard-core taps.
# Plain SDC keeps strict lint vocabulary; unmarked historical kits are unchanged.
set ::ot_vclk_kit_dir [file dirname [file normalize [info script]]]
proc ot_core_tap_bind {corner} {
  set sdc [file join $::ot_vclk_kit_dir constraint.sdc]
  if {![file isfile $sdc]} { return }
  set fd [open $sdc r]; set text [read $fd]; close $fd
  set markers [regexp -all -inline -line {^# OT_CORE_TAP_CORNER_FILE (.+)$} $text]
  if {![llength $markers]} { return }
  if {[llength $markers] != 2 || [lindex $markers 1] ne "core_taps_ff.sdc"} {
    error "core tap corner: invalid overlay marker"
  }
  if {$corner eq "ff"} {
    set overlay [file join $::ot_vclk_kit_dir core_taps_ff.sdc]
    if {![file isfile $overlay]} { error "core tap corner: missing FF overlay $overlay" }
    read_sdc $overlay
    puts "OT_CORE_TAP_BIND corner ff overlay $overlay"
  } elseif {$corner eq "tt"} {
    foreach line [split $text \n] {
      if {[regexp {^set_clock_latency -source -clock clk [-0-9.]+ \[get_ports [A-Za-z_][A-Za-z0-9_]*\]$} $line]} {
        uplevel #0 $line
      }
    }
  } else {
    error "core tap corner: unsupported corner $corner"
  }
}
proc ot_vclk_bind {corner} {
  set k [expr {$corner eq "ff" ? "OT_VCLK_FF" : "OT_VCLK_TT"}]
  if {![info exists ::env($k)] || ![string is double -strict $::env($k)]} { error "vclk_corner: $k unset or not a number" }
  set vc {}
  foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend vc $c } }
  if {[llength $vc] != 1} { error "vclk_corner: expected exactly one IO virtual clock, found [llength $vc]" }
  set_clock_latency -source $::env($k) [lindex $vc 0]
  ot_core_tap_bind $corner
  puts "OT_VCLK_BIND corner $corner clock [get_full_name [lindex $vc 0]] source_latency $::env($k)"
}
if {[info exists ::env(OT_VCLK_CORNER)] && $::env(OT_VCLK_CORNER) ne ""} { ot_vclk_bind $::env(OT_VCLK_CORNER) }
