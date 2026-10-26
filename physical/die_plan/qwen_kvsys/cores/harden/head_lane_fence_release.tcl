# GENERATED-COPY of physical/die_plan/qwen_kvsys/cores/harden/head_lane_fence_release.tcl (--head-lane-taps):
# PRE_DETAIL_PLACE: remove the GPL lane guide regions (ot_lane_fence_*) so DPL legalises freely; lanes stay where GPL
# compacted them.
uplevel #0 {
set lr_blk [ord::get_db_block]
set lr_n 0
foreach r [$lr_blk getRegions] {
  if {![string match ot_lane_fence_* [$r getName]]} continue
  foreach g [$r getGroups] {
    foreach i [$g getInsts] { $g removeInst $i }
    odb::dbGroup_destroy $g
  }
  odb::dbRegion_destroy $r
  incr lr_n
}
puts "OT_LANE_FENCE released $lr_n lane regions before detailed placement"
}
