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
set din {}
foreach p [all_inputs] { if {[get_full_name $p] ni $clock_ports} { lappend din $p } }
if {[llength $din]} { set_input_delay -min -40 -clock [lindex $vclks 0] $din }
if {[llength [all_outputs]]} { set_output_delay -min 0 -clock [lindex $vclks 0] [all_outputs] }
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
