foreach {inst master x y orient} {
  {u_fcore.u_ctl.u_gb} ot_sram_1r1w_128x256_m1_r2c2 38.88 4.332 R0
  {u_fcore.u_ctl.u_xb} ot_sram_1r1w_128x256_m1_r2c2 211.896 4.332 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}

# DIE-HBM-89 lanec_vM2: corner segments dropped (see ot_macro_m4_ring). DIE-HBM-86 lanec_vM1 (FORM_MACRORING.json): the SRAM M4 OBS starts 72 nm inside the macro edge and M5 tracks run inside that ring,
# so a V45 pad between pin tips lands within spacing of the OBS (lanec_e1 DRC at (38.927,40.284)). M4 obstruction on every
# between-pin track of the ring; pin tracks stay open.
proc ot_macro_m4_ring {inst} {
  set blk [ord::get_db_block]; set l [[ord::get_db_tech] findLayer M4]
  set i [$blk findInst $inst]; set b [$i getBBox]; set m [$i getMaster]
  set bx [$b xMin]; set by [$b yMin]; set bX [$b xMax]; set bY [$b yMax]; set W [expr {$bX-$bx}]; set n 0
  foreach side {W E} {
    set ys {}
    foreach mt [$m getMTerms] { foreach mp [$mt getMPins] { foreach g [$mp getGeometry] {
      if {[$g getTechLayer] eq "NULL" || [[$g getTechLayer] getName] ne "M4"} continue
      set xa [$g xMin]; set xb [$g xMax]
      if {($side eq "W" && $xa==0) || ($side eq "E" && $xb==$W)} { lappend ys [list [expr {$by+[$g yMin]}] [expr {$by+[$g yMax]}]] }
    } } }
    if {[llength $ys]==0} continue
    set x0 [expr {$side eq "W" ? $bx : $bX-72}]; set x1 [expr {$x0+72}]
    # DIE-HBM-89 lanec_vM2: the ring now ends one pitch beyond the first / last pin.  vM1 routed DRC: 8 M4 Metal Spacing, all at the two
    # corner segments (macro edge -> first pin, last pin -> macro edge) of both SRAMs, W and E (x 38.88/133.68/211.9/306.7,
    # y by+0.744 / last pin+0.024), stable from DRT iteration 10.  Only the between-pin segments stay.
    # Each end keeps ONE between-pin-sized segment against a virtual pin one 96-nm pitch beyond the first / last pin
    # (same 24-nm OBS as the interior, which routed clean); the long corner run to the macro edge is gone.
    set ys [lsort -integer -index 0 $ys]
    set f [lindex $ys 0]; set e [lindex $ys end]
    set ys [concat [list [list [expr {[lindex $f 0]-96}] [expr {[lindex $f 1]-96}]]] $ys [list [list [expr {[lindex $e 0]+96}] [expr {[lindex $e 1]+96}]]]]
    set prev [lindex $ys 0 1]
    foreach r [lrange $ys 1 end] {
      set y0 [expr {$prev+24}]; set y1 [expr {[lindex $r 0]-24}]
      if {$y1>$y0} { odb::dbObstruction_create $blk $l $x0 $y0 $x1 $y1; incr n }
      set prev [lindex $r 1]
    }
  }
  puts "OT_MACRO_M4_RING $inst obstructions $n"
}
foreach inst {u_fcore.u_ctl.u_gb u_fcore.u_ctl.u_xb} { ot_macro_m4_ring $inst }
