# HBM-ELEM13/SMH-R6 r6 PRE_DETAIL_PLACE hook (kit pre_dpl_extra, after out_flop_release): report how many cells of every
# r6 band group global placement left inside its band, then dissolve the groups and regions so the resizer's buffers
# (3_4, ungrouped) and the legaliser work on the open outline.  Verified on the ORFS image (fencetest 10-21: GPL keeps
# every grouped cell inside its INCLUSIVE region; a dissolved region costs ~1 % boundary spill at DPL).  Placement only.
set ot_r6_blk [ord::get_db_block]
set ot_r6_dbu [$ot_r6_blk getDbUnitsPerMicron]
set ot_r6_n 0
foreach ot_r6_g [$ot_r6_blk getGroups] {
  set gn [$ot_r6_g getName]
  if {![string match r6_* $gn]} continue
  set r [$ot_r6_g getRegion]
  set bx [lindex [$r getBoundaries] 0]
  set x0 [$bx xMin]; set y0 [$bx yMin]; set x1 [$bx xMax]; set y1 [$bx yMax]
  set in 0; set out 0
  foreach i [$ot_r6_g getInsts] {
    set b [$i getBBox]
    if {[$b xMin] >= $x0 && [$b xMax] <= $x1 && [$b yMin] >= $y0 && [$b yMax] <= $y1} { incr in } else { incr out }
  }
  puts "R6_FENCE_GPL group=$gn inside=$in outside=$out box=[expr {$x0/double($ot_r6_dbu)}],[expr {$y0/double($ot_r6_dbu)}],[expr {$x1/double($ot_r6_dbu)}],[expr {$y1/double($ot_r6_dbu)}]"
  odb::dbGroup_destroy $ot_r6_g
  incr ot_r6_n
}
foreach ot_r6_r [$ot_r6_blk getRegions] {
  if {[string match r6_* [$ot_r6_r getName]]} { odb::dbRegion_destroy $ot_r6_r }
}
puts "R6_FENCE_DISSOLVED groups=$ot_r6_n"
if {$ot_r6_n == 0} { error "R6_FENCE: no r6 band groups found at PRE_DETAIL_PLACE (fence hook did not run)" }
