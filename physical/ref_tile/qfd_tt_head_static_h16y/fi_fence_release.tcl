# QW-H16Y PRE_DETAIL_PLACE: release the fixed-issue fence (dbRegion fi_fence / dbGroup fi_fence_grp) after global placement
# put the cluster in its box, before DPL / CTS (as tools/landed_parent/lp_fence_release.tcl): placed cells stay; CTS /
# repair buffers are then free to sit beside their sinks.
set ::fifr_blk [ord::get_db_block]
set ::fifr_i 0
foreach g [$::fifr_blk getGroups] {
  if {[$g getName] ne "fi_fence_grp"} continue
  foreach i [$g getInsts] { $g removeInst $i; incr ::fifr_i }
  odb::dbGroup_destroy $g
}
foreach r [$::fifr_blk getRegions] {
  if {[$r getName] eq "fi_fence"} { odb::dbRegion_destroy $r }
}
puts "FI_FENCE_RELEASE: $::fifr_i instances released"
