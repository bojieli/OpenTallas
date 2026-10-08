# POST_PDN for the H16 quad parent: pdngen cuts the parent M9 straps at each quad (the abstract obstructs M1-M9),
# leaving the quad's full-height M9 VDD/VSS pins 0.08 um short of the strap ends.  The quads sit on the parent's
# 5.4 um M9 lattice (macro_placement_p16a.tcl), so each such pin is extended 0.5 um past the quad edge, on its own
# rectangle only, to overlap the aligned parent strap.  Pins ending inside the quad are left alone.
set ot_blk [ord::get_db_block]
set ot_m9 [[$ot_blk getTech] findLayer M9]
set ot_ext 500
set ot_n 0
foreach ot_i [$ot_blk getInsts] {
  if {[[$ot_i getMaster] getName] ne "ot_attn_tile_m6h1q"} {continue}
  set ot_bb [$ot_i getBBox]
  set ylo [$ot_bb yMin]; set yhi [$ot_bb yMax]
  foreach ot_t [$ot_i getITerms] {
    set ot_net [$ot_t getNet]
    if {$ot_net eq "NULL" || $ot_net eq ""} {continue}
    set ot_st [$ot_net getSigType]
    if {$ot_st ne "POWER" && $ot_st ne "GROUND"} {continue}
    set ot_sw [lindex [$ot_net getSWires] 0]
    foreach ot_lg [$ot_t getGeometries] {
      lassign $ot_lg ot_l ot_g
      if {[$ot_l getName] ne "M9"} {continue}
      set x0 [$ot_g xMin]; set x1 [$ot_g xMax]; set y0 [$ot_g yMin]; set y1 [$ot_g yMax]
      if {$y0 - $ylo < 1000} {
        odb::dbSBox_create $ot_sw $ot_m9 $x0 [expr {$ylo - $ot_ext}] $x1 [expr {$y0 + 200}] STRIPE
        incr ot_n
      }
      if {$yhi - $y1 < 1000} {
        odb::dbSBox_create $ot_sw $ot_m9 $x0 [expr {$y1 - 200}] $x1 [expr {$yhi + $ot_ext}] STRIPE
        incr ot_n
      }
    }
  }
}
puts "OT_QUAD_M9_BRIDGES $ot_n"
