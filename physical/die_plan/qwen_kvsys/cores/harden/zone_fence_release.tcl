# PATH-KV-ASTK2 10-25: PRE_DETAIL_PLACE: remove the GPL zone guide regions (ot_zone_fence_*) so DPL legalises freely;
# zones stay where GPL compacted them.
uplevel #0 {
set zr_blk [ord::get_db_block]
set zr_n 0
foreach r [$zr_blk getRegions] {
  if {![string match ot_zone_fence_* [$r getName]]} continue
  foreach g [$r getGroups] {
    foreach i [$g getInsts] { $g removeInst $i }
    odb::dbGroup_destroy $g
  }
  odb::dbRegion_destroy $r
  incr zr_n
}
puts "OT_ZONE_FENCE released $zr_n zone regions before detailed placement"
}
