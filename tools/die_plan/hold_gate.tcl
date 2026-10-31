# FF-only post-CTS structural hold gate, before any hold repair (owner 2026-10-25 00:46).
if {![info exists ::env(PLIBS)] || ![llength $::env(PLIBS)]} { error "hold gate: BC_LIB_FILES missing" }
foreach l $::env(PLIBS) { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
# FLOW 10-25: the FF gate times the IO paths against the FF-bound vclk (ruling 9.7 / 5e) on the kit's RC basis
if {[info exists ::env(OT_VCLK_FF)] && $::env(OT_VCLK_FF) ne ""} {
  source [file join [file dirname [file normalize [info script]]] vclk_corner.tcl]
  ot_vclk_bind ff
}
if {[info exists ::env(LAYER_PARASITICS_FILE)] && $::env(LAYER_PARASITICS_FILE) ne ""} {
  source $::env(LAYER_PARASITICS_FILE)
} else {
  source $::env(PLATFORM_DIR)/setRC.tcl
}
estimate_parasitics -placement
# Match signoff.py's fixed boundary contract; uncertainty is already in the SDC.
set vclks {}; set clock_ports {}
foreach c [all_clocks] {
  set src [get_property $c sources]
  if {![llength $src]} { lappend vclks $c }
  foreach s $src { lappend clock_ports [get_full_name $s] }
}
if {[llength $vclks] != 1} { error "hold gate: expected one IO virtual clock" }
# FLOW-16 10-31 (same scope as signoff._fwd_ring_tcl, COORD 10-29 21:11 (3)): source-synchronous landing-ring inputs
# (golden SDC tag # OT_FWD_RING_INPUTS <fclk> <ports>) stay timed against their forwarded write clock. The vclk overlay
# below would replace their forwarded-clock input delays (OpenSTA drops the other-clock delays of a port), which hid
# every ring-write hold path from this gate (HEAD l47 hd_turn_a: gate -57/2 vs kit SDC -185/2274, GRT RSZ-0060).
set hg_fwd {}; set hg_fwd_ports {}; set hg_ring_in ""
set hg_gold [file join [file dirname [file normalize [info script]]] constraint.sdc]
if {[info exists ::env(OT_GOLDEN_SDC)] && $::env(OT_GOLDEN_SDC) ne ""} { set hg_gold $::env(OT_GOLDEN_SDC) }
if {[file exists $hg_gold]} {
  set f [open $hg_gold]; set hg_txt [read $f]; close $f
  foreach line [split $hg_txt "\n"] {
    # S81-RINGHOLD-3 opt-in plan clock.ring_hold: the measured sender data-vs-fclk min replaces the seam fallback
    if {[regexp {^# OT_FWD_RING_MIN (\S+)$} $line -> hg_ring_in]} continue
    if {![string match {# OT_FWD_RING_INPUTS *} $line]} continue
    set w [regexp -all -inline {\S+} $line]
    if {[llength $w] < 4} { error "hold gate: malformed OT_FWD_RING_INPUTS line: $line" }
    lappend hg_fwd [list [lindex $w 2] [lrange $w 3 end]]
    foreach s [lrange $w 3 end] { foreach q [get_ports $s] { lappend hg_fwd_ports [get_full_name $q] } }
  }
}
set din {}
foreach p [all_inputs] { if {[get_full_name $p] ni $clock_ports && [get_full_name $p] ni $hg_fwd_ports} { lappend din $p } }
# CLOCK-RESET IO-HOLD 10-25: the kit's seam hold contract (gen_phys.seam_hold via config.mk); legacy -40 / 0
set hg_in -40; set hg_out 0
if {[info exists ::env(OT_HOLD_IN_MIN)] && $::env(OT_HOLD_IN_MIN) ne ""} { set hg_in $::env(OT_HOLD_IN_MIN) }
if {[info exists ::env(OT_HOLD_OUT_MIN)] && $::env(OT_HOLD_OUT_MIN) ne ""} { set hg_out $::env(OT_HOLD_OUT_MIN) }
# plan clock.tap_window (gen_phys.tap_window_ps): the SDC min output delay is the contract + W (the clock ports are
# timed W early), so the waiver guard applies to the contract part
set hg_win 0
if {[info exists ::env(OT_TAP_WINDOW)] && $::env(OT_TAP_WINDOW) ne ""} { set hg_win $::env(OT_TAP_WINDOW) }
if {$hg_out - $hg_win > 0} { error "hold gate: min output delay $hg_out - window $hg_win > 0 waives the sender hold check" }
puts "OT_HOLD_GATE contract in_min $hg_in out_min $hg_out"
if {[llength $din]} { set_input_delay -min $hg_in -clock [lindex $vclks 0] $din }
# IO-HOLD option A (opt-in, gen_phys.io_hold_tcl): partition-driven inputs carry their sender's guaranteed output-min
set ioh [file join [file dirname [file normalize [info script]]] io_hold.tcl]
if {[file exists $ioh]} { source $ioh; ot_io_hold_apply [lindex $vclks 0] }
if {[llength [all_outputs]]} { set_output_delay -min $hg_out -clock [lindex $vclks 0] [all_outputs] }
# the ring inputs get the same overlay min on their own forwarded clock (signoff._fwd_ring_tcl), after io_hold.tcl
if {$hg_ring_in eq ""} { set hg_ring_in $hg_in }
foreach r $hg_fwd { lassign $r ck sels; foreach s $sels { set_input_delay -min $hg_ring_in -clock [get_clocks $ck] [get_ports $s] } }
if {[llength $hg_fwd]} { puts "OT_HOLD_GATE forwarded ring inputs [llength $hg_fwd_ports] on [llength $hg_fwd] clock(s), min $hg_ring_in" }
# A separate FF-only process: do not impersonate the shared multi-mode context.
# Owner thresholds match orfs_hold_mm.tcl, applied to actual negative endpoints.
set w [sta::time_sta_ui [sta::worst_slack_cmd min]]
set n [sta::endpoint_violation_count min]
if {![string is double -strict $w] || ![string is integer -strict $n]} {
  error "hold gate: true FF hold statistics unavailable"
}
if {$w < -100.0 || $n > 2000} {
  puts [format "OT_HOLD_GATE FAIL FF wns_ps %.2f endpoints %d (true negative slack)" $w $n]
  error "structural FF hold failure: revise plan/RTL/boundary before repair"
}
puts [format "OT_HOLD_GATE PASS FF wns_ps %.2f endpoints %d (true negative slack)" $w $n]
