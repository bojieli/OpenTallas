# PRE_FLOORPLAN only: 1_synth has no placed RC or realized reset tree.
# The pinned ORFS floorplan size-only setup pass cannot buffer recovery nets;
# it can repeat indefinitely after exhausting cell sizes (QC SU:8341 RESETN).
# Placement/CTS/GRT run in separate processes and retain all normal repairs.
if {![llength [info commands repair_timing_helper]]} {
  error "UNPLACED_SETUP_GUARD: pinned ORFS repair_timing_helper missing"
}
if {[llength [info commands ot_floorplan_repair_timing_helper]]} {
  error "UNPLACED_SETUP_GUARD: duplicate installation"
}
rename repair_timing_helper ot_floorplan_repair_timing_helper
proc repair_timing_helper {args} {
  set seq [lsearch -exact $args -sequence]
  if {[lsearch -exact $args -setup] >= 0 && [lsearch -exact $args -hold] < 0 &&
      $seq >= 0 && [lindex $args [expr {$seq + 1}]] eq {unbuffer,sizeup,swap,vt_swap}} {
    foreach inst [[ord::get_db_block] getInsts] {
      if {[$inst isPlaced]} {
        error "UNPLACED_SETUP_GUARD: refusing skip on placed design"
      }
    }
    puts "UNPLACED_SETUP_GUARD: skipped floorplan size-only setup pass before placed RC/reset realization; all later setup/hold checks remain enabled"
    return
  }
  uplevel 1 [list ot_floorplan_repair_timing_helper {*}$args]
}
