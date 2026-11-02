# Normal PRE_DETAIL_PLACE release: legalization/repair remain free; no FF moves.
set b [ord::get_db_block]
set nr 0
foreach r [$b getRegions] {
  if {![string match ot_ctl_comb_road_* [$r getName]]} continue
  foreach g [$r getGroups] {
    foreach i [$g getInsts] {$g removeInst $i}
    odb::dbGroup_destroy $g
  }
  odb::dbRegion_destroy $r
  incr nr
}
if {$nr!=6} {error "CTL_COMB_ROAD release expected6 own regions got$nr"}
puts "CTL_COMB_ROAD_RELEASED $nr regions; ordinary DPL/repair free"
