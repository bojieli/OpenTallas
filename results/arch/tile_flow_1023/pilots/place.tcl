# TILE-FLOW diagnostic placement probe (read-only input): the kit's PRE_GLOBAL_PLACE (io_flop_at_pins + face fence),
# global + detailed placement, then the TILE-RENDER dump (tv2.tcl) of the placed db.
read_db /in/in.odb
set ::env(RESULTS_DIR) /work
source /work/hooks.tcl
global_placement -density $::env(PD) -skip_initial_place -pad_left 0 -pad_right 0
if {[info exists ::env(OT_POST_GPL)] && $::env(OT_POST_GPL) ne ""} { source $::env(OT_POST_GPL) }
detailed_placement
set b [ord::get_db_block]
foreach g [$b getGroups] {
  set r [$g getRegion]; if {$r eq "NULL"} continue; set bx [lindex [$r getBoundaries] 0]
  set out 0; set n 0
  foreach i [$g getInsts] { incr n; set bb [$i getBBox]
    if {[$bb xMin] < [$bx xMin] || [$bb xMax] > [$bx xMax] || [$bb yMin] < [$bx yMin] || [$bb yMax] > [$bx yMax]} { incr out } }
  puts "PROBE_FENCE [$g getName] $n insts, outside band: $out"
}
write_db /work/placed.odb
