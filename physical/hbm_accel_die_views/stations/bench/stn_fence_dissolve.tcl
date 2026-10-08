# POST_GLOBAL_PLACE hook (stn_route.sh FENCE=1): the FIFO fence (stn_meso_fence.tcl) only steers global placement.
# Dissolve its group and region once global placement is done, so the resizer's buffers and the legaliser work on
# the open outline (r11: DPL-0033 "placed in rows" with the region kept, its edges off the row grid).
set ot_blk [ord::get_db_block]
foreach ot_g [$ot_blk getGroups] {
  if {[string match ot_fence_grp_* [$ot_g getName]]} { odb::dbGroup_destroy $ot_g }
}
foreach ot_r [$ot_blk getRegions] {
  if {[string match ot_fence_* [$ot_r getName]]} {
    puts "OT_STN: dissolve [$ot_r getName] after global placement"
    odb::dbRegion_destroy $ot_r
  }
}
