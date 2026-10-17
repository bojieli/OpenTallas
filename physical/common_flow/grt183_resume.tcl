# GRT183-RESUME (ROOT 2026-10-15): sourced by hooks/pre_grt_ot_grt183.tcl (tools/run_abi3_physical.py) at ORFS PRE
# GLOBAL_ROUTE, after the block's own PRE_GLOBAL_ROUTE hook.
#
# Defect: GRT-0183 ("3D maze router ran out of legal paths (heap underflow)") raised by the INCREMENTAL global route that
# repair_design / repair_timing run inside stage 5_1_grt kills the stage although the full global route of the same
# design has zero overflow.  Measured on qfd_tt_scale_leaf-tg1-b123d97bd (ot-epyc1tb:/srv/opentallas/claude/
# tt-boundary-2116): initial full GRT 8.99 % usage, 0 overflow; repair_design up-sized scale_addr[166] DFFHQNx1->x2 at
# an unchanged location and the incremental reroute of _04241_ hit GRT-0183.  In the same process neither
# global_route -end_incremental (SIGSEGV in GlobalRouter::endIncremental) nor a new full global_route (GRT-0171) recovers;
# a FRESH process that full-global-routes the saved resized design and runs the complete repair_design passes
# (0 overflow, 137 slew violations repaired, RECOVERY_PASS_C).
#
# This hook only SAVES the resized design ($RESULTS_DIR/5_1_grt.grt183_resume.odb) and re-raises the error, so the stage
# still fails; tools/run_abi3_physical.py then re-runs the whole 5_1_grt stage ONCE, in a fresh process, from that
# design (every repair re-runs: no mutation discarded, no repair skipped, no guard or limit changed).  A second GRT-0183
# (marker 5_1_grt.grt183_recovered.json present) is not saved again: the route fails as before (fail-closed).
#
# Sourced BEFORE the block's own PRE_GLOBAL_ROUTE hook: it records the routing obstructions and placement blockages the
# stage started with; the saved design drops the ones the block's hook added (keepouts / macro edge guards, which the
# re-run's PRE hook re-creates from unchanged pins and macros -- macro_edge_via_guard.tcl refuses a second add), so the
# re-run starts from exactly the stage's input state plus the repair mutations.
namespace eval ot_g183 {
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
  variable start {}
  foreach {k o} [keys] { dict incr start $k }
  proc strip_hook_shapes {} {
    variable start; set seen {}; set n 0
    foreach {k o} [keys] {
      dict incr seen $k
      if {[dict get $seen $k] > ([dict exists $start $k] ? [dict get $start $k] : 0)} {
        if {[lindex $k 0] eq "O"} { odb::dbObstruction_destroy $o } else { odb::dbBlockage_destroy $o }
        incr n
      }
    }
    return $n
  }
}
foreach ot_g183_helper {repair_design_helper repair_timing_helper} {
  if {[llength [info commands $ot_g183_helper]] && ![llength [info commands ot_g183_orig_$ot_g183_helper]]} {
    rename $ot_g183_helper ot_g183_orig_$ot_g183_helper
    proc $ot_g183_helper {args} [string map [list @H@ $ot_g183_helper] {
      set rc [catch {uplevel 1 [linsert $args 0 ot_g183_orig_@H@]} msg opts]
      if {$rc == 0} { return $msg }
      set dir $::env(RESULTS_DIR)
      if {[string match "*GRT-0183*" $msg] && ![file exists $dir/5_1_grt.grt183_recovered.json]} {
        set ot_n [ot_g183::strip_hook_shapes]
        write_db $dir/5_1_grt.grt183_resume.odb
        puts "OT_GRT183_RESUME_SAVED helper=@H@ odb=$dir/5_1_grt.grt183_resume.odb hook_shapes_dropped=$ot_n: incremental GRT-0183 inside @H@; the runner re-runs 5_1_grt once in a fresh process from this resized design"
      } elseif {[string match "*GRT-0183*" $msg]} {
        puts "OT_GRT183_RESUME_REFUSED helper=@H@: GRT-0183 again after one fresh-process resume; not retried"
      }
      return -options $opts $msg
    }]
  }
}
unset ot_g183_helper
