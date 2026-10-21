# PRE_DETAIL_PLACE hook (HBM-QCORE8 2026-10-20, pslice_c5 r10): release the lp.py landing fences (dbRegion/dbGroup lp_fence_*) after
# global placement (GPL put every landing cell in its box), BEFORE the placement DPL and CTS (also avoids r9a DPL-0033).  The fences are EXCLUSIVE: r9b (lp9b, ot-epyc5 10-19/20) kept
# every CTS buffer of ck_c<k>_regs OUT of the 21.6-um landing strips, so the post-CTS detailed_placement (6,416 violations)
# pushed the region trees' buffers away and the soft insertion grew ~360 ps on the L-leaf roots (c1 TT 534 -> 901 ps at the
# same child pin 477..540) = the soft-vs-child clock-rule FAIL.  Placed cells stay where GPL/DPL put them (legal sites);
# CTS / repair buffers are then free to sit beside their sinks.
set ::lpfr_blk [ord::get_db_block]
set ::lpfr_g 0
set ::lpfr_i 0
foreach g [$::lpfr_blk getGroups] {
  if {![string match lp_fence_grp_* [$g getName]]} continue
  foreach i [$g getInsts] { $g removeInst $i; incr ::lpfr_i }
  odb::dbGroup_destroy $g
  incr ::lpfr_g
}
set ::lpfr_r 0
foreach r [$::lpfr_blk getRegions] {
  if {![string match lp_fence_* [$r getName]]} continue
  odb::dbRegion_destroy $r
  incr ::lpfr_r
}
puts "LP_FENCE_RELEASE groups=$::lpfr_g regions=$::lpfr_r insts=$::lpfr_i (before DPL/CTS)"
if {$::lpfr_g == 0} { puts "LP_FENCE_RELEASE WARNING: no lp_fence groups found" }
