# POST_PDN (hfd_attn_tile, CLAUDE HBM-ABSTRACTS attn): pdngen stops the tile's M8 straps short of each quad (macro
# blockage, trimmed back to the last M7 contract crossing: measured 0.26-8.36 um on fp_p3), so the quads' M8 PG edge
# stubs (ot_attn_tile_m6h1q LEF: one 0.04 x 0.474 um stub at each end of every internal M8 PG strap) would float.
# The quads sit on the tile's PG lattice (macro_placement.tcl), so every stub faces a tile strap of its own net on the
# same track: bridge each stub outward to the nearest such strap end (an M8 strap segment, at most OT_MAXGAP um).
set ot_blk [ord::get_db_block]
set ot_dbu [$ot_blk getDbUnitsPerMicron]
set ot_m8 [[ord::get_db_tech] findLayer M8]
set ot_maxgap [expr {int(15.0 * $ot_dbu)}]
# tile M8 straps per net, keyed by track "yMin yMax"
foreach ot_n {VDD VSS} {
  set ot_s($ot_n) [dict create]
  foreach ot_sw [[$ot_blk findNet $ot_n] getSWires] { foreach ot_w [$ot_sw getWires] {
    if {[$ot_w isVia] || [$ot_w getTechLayer] ne $ot_m8} {continue}
    dict lappend ot_s($ot_n) "[$ot_w yMin] [$ot_w yMax]" [list [$ot_w xMin] [$ot_w xMax]] } }
}
set ot_nb 0; set ot_gmax 0
foreach ot_i [$ot_blk getInsts] {
  if {[[$ot_i getMaster] getName] ne "ot_attn_tile_m6h1q"} {continue}
  set ot_bb [$ot_i getBBox]
  set ot_bx0 [$ot_bb xMin]; set ot_bx1 [$ot_bb xMax]; set ot_by0 [$ot_bb yMin]
  set ot_mw [[$ot_i getMaster] getWidth]
  set ot_or [$ot_i getOrient]
  if {$ot_or ne "R0" && $ot_or ne "MY"} { error "bridge_quad_m8: orientation $ot_or not handled" }
  foreach ot_t [$ot_i getITerms] {
    set ot_mt [$ot_t getMTerm]
    set ot_sig [$ot_mt getSigType]
    if {$ot_sig ne "POWER" && $ot_sig ne "GROUND"} {continue}
    set ot_net [$ot_t getNet]
    if {$ot_net eq "NULL" || $ot_net eq ""} { error "bridge_quad_m8: [$ot_i getName] [$ot_mt getName] not connected" }
    set ot_nn [$ot_net getName]
    set ot_sw [odb::dbSWire_create $ot_net ROUTED]
    foreach ot_mp [$ot_mt getMPins] {
      foreach ot_g [$ot_mp getGeometry] {
        if {[$ot_g getTechLayer] ne $ot_m8} {continue}
        set ot_lx0 [$ot_g xMin]; set ot_lx1 [$ot_g xMax]
        if {$ot_lx1 - $ot_lx0 > int(0.1 * $ot_dbu)} {continue}
        if {$ot_or eq "R0"} { set ot_x0 [expr {$ot_bx0 + $ot_lx0}]; set ot_x1 [expr {$ot_bx0 + $ot_lx1}] } else {
          set ot_x0 [expr {$ot_bx0 + $ot_mw - $ot_lx1}]; set ot_x1 [expr {$ot_bx0 + $ot_mw - $ot_lx0}] }
        set ot_y0 [expr {$ot_by0 + [$ot_g yMin]}]; set ot_y1 [expr {$ot_by0 + [$ot_g yMax]}]
        set ot_k "$ot_y0 $ot_y1"
        if {![dict exists $ot_s($ot_nn) $ot_k]} { error "bridge_quad_m8: [$ot_i getName] $ot_nn stub y $ot_y0..$ot_y1 has no tile M8 strap on its track" }
        set ot_best -1
        if {$ot_x1 >= $ot_bx1 - 2} {
          foreach ot_e [dict get $ot_s($ot_nn) $ot_k] { lassign $ot_e ot_ex0 ot_ex1
            if {$ot_ex0 >= $ot_x1 && ($ot_best < 0 || $ot_ex0 < $ot_best)} { set ot_best $ot_ex0 } }
          if {$ot_best < 0 || $ot_best - $ot_x1 > $ot_maxgap} { error "bridge_quad_m8: [$ot_i getName] $ot_nn stub at x $ot_x1 y $ot_y0: no strap within reach (east)" }
          set ot_gap [expr {$ot_best - $ot_x1}]; set ot_bx $ot_x0; set ot_ex [expr {$ot_best + int(0.474 * $ot_dbu)}]
        } elseif {$ot_x0 <= $ot_bx0 + 2} {
          foreach ot_e [dict get $ot_s($ot_nn) $ot_k] { lassign $ot_e ot_ex0 ot_ex1
            if {$ot_ex1 <= $ot_x0 && $ot_ex1 > $ot_best} { set ot_best $ot_ex1 } }
          if {$ot_best < 0 || $ot_x0 - $ot_best > $ot_maxgap} { error "bridge_quad_m8: [$ot_i getName] $ot_nn stub at x $ot_x0 y $ot_y0: no strap within reach (west)" }
          set ot_gap [expr {$ot_x0 - $ot_best}]; set ot_bx [expr {$ot_best - int(0.474 * $ot_dbu)}]; set ot_ex $ot_x1
        } else {continue}
        if {$ot_gap > $ot_gmax} { set ot_gmax $ot_gap }
        odb::dbSBox_create $ot_sw $ot_m8 $ot_bx $ot_y0 $ot_ex $ot_y1 STRIPE
        incr ot_nb
      }
    }
  }
}
puts "OT_QUAD_M8_BRIDGES $ot_nb max_gap_um [expr {$ot_gmax / double($ot_dbu)}]"
if {$ot_nb != 4 * 2 * 208} { error "bridge_quad_m8: bridged $ot_nb stubs, expected [expr {4 * 2 * 208}]" }
