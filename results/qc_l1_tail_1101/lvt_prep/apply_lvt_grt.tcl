set b [ord::get_db_block]
proc need {ok msg} {if {!$ok} {error $msg}}
proc clock_guides {b} {
 set rows {}
 foreach n [$b getNets] {
  if {[$n getSigType] ne "CLOCK"} continue
  foreach g [$n getGuides] {
   set r [$g getBox]
   lappend rows [list [$n getName] [[$g getLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
  }
 }
 return [lsort $rows]
}
set frozen_clock_guides [clock_guides $b]
set frozen_clock_guides [clock_guides $b]
set_routing_layers -signal M2-M5 -clock M2-M5
global_route -start_incremental
source /work/apply_lvt.tcl
set actual_digest [lindex [exec sha256sum /work/lvt_placement.tsv] 0]
set fh [open /work/reviewed_lvt_placement.sha256];set expected_digest [string trim [read $fh]];close $fh
need [expr {$actual_digest eq $expected_digest}] {LVT placement differs from actual reviewed capsule}
global_route -end_incremental -congestion_iterations 50 -resistance_aware
need [expr {$frozen_clock_guides eq [clock_guides $b]}] {CLOCK guide geometry changed}
estimate_parasitics -global_routing
ot_mm_sync
set setup [ot_mm_ws max [ot_mm_sc]];set hold [ot_mm_ws min BC]
puts [format "L1_LVT_GRT_FINAL TT %.6f FF %.6f" $setup $hold]
ot_mm_unsync
write_sdc -no_timestamp /work/lvt_grt.sdc
write_guides /work/lvt.route.guide
write_db /work/lvt_grt.odb
set fh [open /work/lvt_grt_summary.txt w];puts $fh [format "TT %.6f FF %.6f" $setup $hold];close $fh
puts L1_LVT_GRT_COMPLETE
