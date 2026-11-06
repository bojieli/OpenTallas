# GRT-STALL-RESUME (KW-FIX-17 2026-11-05, COORD 17:2x (6) / 17:4x).  Sourced by grt183_make.sh's disposable copy of
# ORFS global_route.tcl at PRE GLOBAL_ROUTE, BEFORE grt183_resume.tcl (ROOT 10-15, kept byte-identical for ABI 3) and the
# kit's own PRE hook.
#
# Class: ORFS global_route.tcl runs repair_design on GRT parasitics, then 'global_route -end_incremental'; that call can
# spin single-threaded for hours (HBM dma_m6c 637 buffers, S81 dsdv_eng_rr_e_rfg2 1008, QC nk/nl a0c: 5_1_grt.tmp.log flat
# >2 h on that line), while ~560 finished runs took at most 77 min there.
#   1. When repair_design_helper returns, save the resized design ($RESULTS_DIR/5_1_grt.stall_resume.odb) plus the list
#      of routing obstructions / placement blockages the PRE hook(s) added (5_1_grt.stall_resume.shapes).  The live run
#      is not changed.  grt183_make.sh stops a stalled stage and re-runs it ONCE in a fresh process from that design.
#   2. In that re-run (grt183_make.sh renamed the list to 5_1_grt.stall_strip.shapes), drop exactly those shapes first,
#      so the kit's PRE hook re-creates them from unchanged pins and macros, as in the GRT-0183 resume.
# No save after any fresh-process resume (marker 5_1_grt.grt183_recovered.json) or with OT_GRT_STALL_RESUME=0.
namespace eval ot_gstall {
  proc keys {} {
    set b [ord::get_db_block]; set out {}
    foreach o [$b getObstructions] {
      set x [$o getBBox]; set l [$x getTechLayer]
      lappend out [list O [expr {$l eq "NULL" ? "-" : [$l getName]}] [$x xMin] [$x yMin] [$x xMax] [$x yMax]] $o
    }
    foreach o [$b getBlockages] {
      set x [$o getBBox]
      lappend out [list B - [$x xMin] [$x yMin] [$x xMax] [$x yMax]] $o
    }
    return $out
  }
  set dir $::env(RESULTS_DIR)
  if {[file exists $dir/5_1_grt.stall_strip.shapes]} {
    set f [open $dir/5_1_grt.stall_strip.shapes]; set want [read $f]; close $f
    set need {}; foreach k $want { dict incr need $k }
    set kl [keys]; set n 0
    for {set i [expr {[llength $kl] - 2}]} {$i >= 0} {incr i -2} {
      set k [lindex $kl $i]; set o [lindex $kl [expr {$i + 1}]]
      if {[dict exists $need $k] && [dict get $need $k] > 0} {
        dict incr need $k -1
        if {[lindex $k 0] eq "O"} { odb::dbObstruction_destroy $o } else { odb::dbBlockage_destroy $o }
        incr n
      }
    }
    puts "OT_GRT_STALL_RESUMED hook_shapes_dropped=$n of [llength $want]"
  }
  variable start {}
  foreach {k o} [keys] { dict incr start $k }
  proc save {} {
    set dir $::env(RESULTS_DIR)
    if {([info exists ::env(OT_GRT_STALL_RESUME)] && $::env(OT_GRT_STALL_RESUME) eq "0") ||
        [file exists $dir/5_1_grt.grt183_recovered.json]} { return }
    variable start; set seen {}; set hk {}
    foreach {k o} [keys] {
      dict incr seen $k
      if {[dict get $seen $k] > ([dict exists $start $k] ? [dict get $start $k] : 0)} { lappend hk $k }
    }
    set f [open $dir/5_1_grt.stall_resume.shapes w]; puts $f $hk; close $f
    write_db $dir/5_1_grt.stall_resume.odb
    puts "OT_GRT_STALL_SAVED odb=$dir/5_1_grt.stall_resume.odb hook_shapes=[llength $hk]: fresh-process resume point if the incremental route stalls"
  }
}
if {[llength [info commands repair_design_helper]] && ![llength [info commands ot_gstall_orig_repair_design_helper]]} {
  rename repair_design_helper ot_gstall_orig_repair_design_helper
  proc repair_design_helper {args} {
    set r [uplevel 1 [linsert $args 0 ot_gstall_orig_repair_design_helper]]
    ot_gstall::save
    return $r
  }
}
