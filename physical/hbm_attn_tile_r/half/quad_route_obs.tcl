# el1011-hbm-attn v5 (POST_PDN, opt-in QOBS=<inset um>): each attention quad is OPAQUE to the parent router on M4 / M5 / M6
# (inset ot_qobs_um from its edges; all 1,764 quad signal pins are M4 edge pins reaching < 0.5 um in).  The quad LEF
# OBS is porous (M6: 21,714 rects over 25 % of the area; M4 31 %, M5 26 %), so GRT counted M6 capacity over the
# quads that the fragments make unusable and routed horizontal nets straight across them: half_v3 hi v3nb post-repair
# GRT-0232, 1.04 M of 1.16 M overflow on M6 at 14 % M6 use.  Opaque quads push that traffic into the channels the
# floorplan sized for it (fp_margin_lint channel_worst 0.79, quads counted as blocking).  M7 (vertical; quad 6 %)
# stays open for the quad_m7_link PDN and vertical crossings.  A routing obstruction only: no timing exception.
set ot_qobs_block [ord::get_db_block]
set ot_qobs_tech [[ord::get_db] getTech]
set ot_qobs_d [expr {int(round($ot_qobs_um * [$ot_qobs_block getDbUnitsPerMicron]))}]
set ot_qobs_n 0
foreach inst [$ot_qobs_block getInsts] {
  if {[[$inst getMaster] getName] ne "ot_attn_tile_m6h1q"} { continue }
  set bb [$inst getBBox]
  foreach l {M4 M5 M6} {
    odb::dbObstruction_create $ot_qobs_block [$ot_qobs_tech findLayer $l] \
      [expr {[$bb xMin] + $ot_qobs_d}] [expr {[$bb yMin] + $ot_qobs_d}] [expr {[$bb xMax] - $ot_qobs_d}] [expr {[$bb yMax] - $ot_qobs_d}]
    incr ot_qobs_n
  }
}
puts "OT_QOBS: $ot_qobs_n quad routing obstructions (M4-M6, inset $ot_qobs_um um)"
