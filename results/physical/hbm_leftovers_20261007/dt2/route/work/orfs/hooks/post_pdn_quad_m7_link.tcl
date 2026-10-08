# POST_PDN for the bank-built die tile hfd_attn_tile_b (option B): every option-B quad ot_attn_tile_m6h1q carries its
# own M7 VDD / VSS stripes (full height, the die contract grid).  pdngen cuts the tile's M7 contract stripes at each
# quad, so each quad M7 PG stripe is copied into the tile's special wiring, full length and 0.5 um past the quad's
# edges: (1) the copies overlap the cut ends of the tile's own stripes (R0 quads sit exactly on the tile's 10.8 um
# lattice, MY quads within 8 nm of it), joining quad and tile grids, and (2) they are tile M7 PG pins over the quads,
# so the die's M8 straps land on them there too (option A's failure was a quad fed only from its edges).
set ot_blk [ord::get_db_block]
set ot_m7 [[$ot_blk getTech] findLayer M7]
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
      if {[$ot_l getName] ne "M7"} {continue}
      set x0 [$ot_g xMin]; set x1 [$ot_g xMax]; set y0 [$ot_g yMin]; set y1 [$ot_g yMax]
      if {$y0 - $ylo < 1000} { set y0 [expr {$ylo - $ot_ext}] }
      if {$yhi - $y1 < 1000} { set y1 [expr {$yhi + $ot_ext}] }
      odb::dbSBox_create $ot_sw $ot_m7 $x0 $y0 $x1 $y1 STRIPE
      incr ot_n
    }
  }
}
puts "OT_QUAD_M7_LINKS $ot_n"
