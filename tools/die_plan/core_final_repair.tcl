# Final timing repair AFTER every kit/clock/DRV post-GRT mutation. Acceptance is
# still the released TT/FF/DRV policy; this hook changes no constraint or corner.
if {![info exists ::ot_mm_active] || ![llength [info commands ot_mm_sc]] ||
    [string toupper [ot_mm_sc]] ne "TC" || ![llength [info commands repair_timing_helper]]} {
  puts "OT_CORE_FINAL_REPAIR NOT RUN: no active TT/FF two-mode repair session; existing gates unchanged"
  return
}
# Reuse the established overlap-aware clock lock when staged. Older snapshots
# get the same protection locally, without overriding their global DPL command.
proc ot_core_final_legalize {} {
  if {[llength [info commands ::ot_grt_dpl_orig]]} {
    detailed_placement
    check_placement -verbose
    return
  }
  set b [ord::get_db_block]; set candidates {}; set rows {}; set overlaps {}
  foreach n [$b getNets] {
    if {[$n getSigType] ne "CLOCK"} continue
    foreach it [$n getITerms] {
      set i [$it getInst]
      if {[$i getPlacementStatus] eq "PLACED"} {dict set candidates $i 1}
    }
  }
  foreach i [$b getInsts] {
    set mine [dict exists $candidates $i]
    if {!$mine && [$i getPlacementStatus] ni {FIRM LOCKED}} continue
    if {[[$i getMaster] isBlock]} continue
    set bb [$i getBBox]
    dict lappend rows [$bb yMin] [list [$bb xMin] [$bb xMax] $i $mine]
  }
  dict for {y cells} $rows {
    set ux {}; set owner {}
    foreach c [lsort -integer -index 0 $cells] {
      lassign $c x0 x1 i mine
      if {$ux ne {} && $x0 < $ux} {
        if {$mine} {dict set overlaps $i 1}
        if {[lindex $owner 1]} {dict set overlaps [lindex $owner 0] 1}
      }
      if {$ux eq {} || $x1 > $ux} {set ux $x1;set owner [list $i $mine]}
    }
  }
  set locked {}
  dict for {i unused} $candidates {
    if {[dict exists $overlaps $i]} continue
    $i setPlacementStatus FIRM; lappend locked $i
  }
  puts "OT_CORE_FINAL_CLOCK_LOCK [llength $locked] fixed; [dict size $overlaps] resized-overlap instances legalize"
  try {detailed_placement;check_placement -verbose} finally {
    foreach i $locked {$i setPlacementStatus PLACED}
  }
}
puts "OT_CORE_FINAL_REPAIR begin after all post-GRT mutations"
estimate_parasitics -global_routing
ot_mm_sync
set ot_cf_setup [ot_mm_ws max [ot_mm_sc]]
set ot_cf_hold [ot_mm_ws min BC]
ot_mm_unsync
if {$ot_cf_setup >= 0 && $ot_cf_hold >= 0} {
  puts "OT_CORE_FINAL_REPAIR already meets nominal TT/FF; no margin-only repair (released policy still required)"
  return
}
# A preceding DPL/resizer pass can leave pending invalid-net callbacks even
# after bulk global-route RC estimation. Rebuild through the native placement
# estimator, which drains that state, then restore actual global-route RC before
# entering another incremental repair. Never time/repair on the temporary
# placement estimate, clear estimator flags, or catch an EST consistency error.
puts "OT_CORE_FINAL_REPAIR rebuild native estimator state; final RC remains global_routing"
estimate_parasitics -placement
estimate_parasitics -global_routing
global_route -start_incremental
# Do not unbuffer the just-repaired slew nets. Keep the existing per-mode FF
# hold guard and requested margins while repairing TT data paths.
repair_timing_helper -setup -sequence {sizeup swap split buffer}
repair_timing_helper -hold
ot_core_final_legalize
global_route -end_incremental -resistance_aware
estimate_parasitics -global_routing
# Report the actual final parasitics, not the earlier pre-DRV repair result.
ot_mm_sync
puts [format "OT_CORE_FINAL_REPAIR final TT %.2f FF %.2f ps (released policy still required)" [ot_mm_ws max [ot_mm_sc]] [ot_mm_ws min BC]]
ot_mm_unsync
report_check_types -max_slew -max_capacitance -violators
if {![llength [info commands ot_pg_connect_all]]} {source /work/pg_connect.tcl}
ot_pg_connect_all core_final_repair
ot_pg_require_bound core_final_repair
if {[info exists ::env(OT_RESET_PAIR_FIXED)] && $::env(OT_RESET_PAIR_FIXED) eq "1" &&
    [llength [info commands ot_reset_pair_verify_hops]]} {
  ot_reset_pair_verify_hops [ord::get_db_block] 405
}
