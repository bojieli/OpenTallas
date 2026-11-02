# Dispatch-only coupon from the EXACT failed helper. All STA operations are stubs; no timing/Lib credit.
set root [file dirname [file normalize [info script]]]
source [file join $root orfs_hold_mm_failure.tcl]
set ::env(OT_HOLD_MM) 1
set ::env(OT_MM_SETUP_CORNER) tc
set ::env(TC_LIB_FILES) fixture_TT
set ::env(BC_LIB_FILES) fixture_FF
set ::env(RESULTS_DIR) $root
set ::env(OT_MM_IOREF_FILE) [file join $root absent_ioref]
set ::env(OT_MM_MEASURED_HOLD) 0
unset -nocomplain ::env(OT_MM_FF_SDC)
proc set_mode {m} {set ::mode $m}
proc define_scene {args} {lappend ::scenes $args}
proc log_cmd {args} {uplevel 1 $args}
proc read_sdc {args} {lappend ::sdc_reads $args}
proc all_clocks {} {return clk}
proc set_false_path {args} {lappend ::false_paths [linsert $args 0 $::mode]}
proc set_propagated_clock {args} {}
proc write_sdc {args} {set f [open [lindex $args end] w];puts $f "# stub";close $f}
proc estimate_parasitics {args} {lappend ::rc_args $args}
proc ot_mm_scene_shim {args} {}
proc ot_mm_sync_link_periods {} {}
proc ot_mm_ws {args} {return 0.0}
foreach base {final_grt.sdc 4_cts.sdc 3_place.sdc} {
 set ::scenes {};set ::sdc_reads {};set ::false_paths {};set ::rc_args {}
 unset -nocomplain ::ot_mm_active ::ot_mm_synced ::ot_mm_stage
 ot_mm_read_sdc [file join $root $base]
 ot_mm_sync
 set disabled 0
 foreach f $::false_paths {if {[lindex $f 0] eq "ff" && [lindex $f 1] eq "-hold"} {set disabled 1}}
 set synced [info exists ::ot_mm_synced]
 puts "CASE $base stage=$::ot_mm_stage ff_hold_disabled=$disabled synced=$synced rc=$::rc_args scenes=$::scenes"
 if {$base eq "final_grt.sdc"} {if {!$disabled || $synced || [llength $::rc_args]} {error "failedcase not reproduced"}}
 if {$base eq "4_cts.sdc"} {if {$disabled || !$synced || $::rc_args ne "-global_routing -global_routing"} {error "normalGRT context not restored"}}
 if {$base eq "3_place.sdc"} {if {!$synced || $::rc_args ne "-placement -placement"} {error "wrongstage RC control failed"}}
}
puts "DISPATCH_FIXTURE_PASS failure_reproduced normalGRT_alias_recognized wrongPlacementRole_control_detected"
