# DIE-HBM-83-COLL gqi vD (OWNER 11-06 22:0x smells 2/8): SE corner relief, kit-local, 0 cycles, netlist unchanged.
# Measured on vA 5_1_grt.odb: all 1282 DRT violations at it50 sit in x 156-168, y 4-24; local cell util there 0.85-1.07.
# The E band (aq0_x, 10.4 pins/um down to y 1.1) and the S band (aq0_q, up to x 171.7) both clamp into that corner.
# Every FIRM face flop in the window moves to the nearest free cell of a sparser grid (40 sites x 2 rows, 25% flop util).
# Flops farthest from the corner go first, so band flops stay close to their pins and the corner flops move inward.
# Sourced from face_flops.tcl after the face flops are placed (ff_blk ff_dbu ff_x1 ff_y0 ff_sw ff_rh ff_orient in scope).
set cr_w [expr {round(32.0 * $ff_dbu)}]; set cr_h [expr {round(36.0 * $ff_dbu)}]
set cr_xl [expr {$ff_x1 - $cr_w}]; set cr_yh [expr {$ff_y0 + $cr_h}]
set cr_cp [expr {$ff_sw * 40}]; set cr_rp [expr {$ff_rh * 2}]
set cr_ncol [expr {int(($cr_w - 21 * $ff_sw) / $cr_cp) + 1}]
set cr_nrow [expr {int(($cr_h - $ff_rh) / $cr_rp) + 1}]
set cr_c0 [expr {($ff_x1 - $ff_x0 - 21 * $ff_sw) / $ff_sw}]
set cr_todo {}
set fh [open $::env(RESULTS_DIR)/ot_face_flops.txt r]
foreach ln [split [read $fh] "\n"] {
  if {$ln eq ""} continue
  set i [$ff_blk findInst [lindex [split $ln "\t"] 0]]
  if {$i eq "NULL" || $i eq "" || [$i getPlacementStatus] ne "FIRM"} continue
  set b [$i getBBox]; set x [$b xMin]; set y [$b yMin]
  if {$x + [$b getDX] / 2 < $cr_xl || $y + [$b getDY] / 2 >= $cr_yh} continue
  # distance from the SE corner, farthest first
  lappend cr_todo [list [expr {max($ff_x1 - $x, 0) + max($y - $ff_y0, 0)}] $x $y [$i getName]]
}
close $fh
set cr_todo [lsort -integer -decreasing -index 0 $cr_todo]
set cr_occ {}; set cr_n 0; set cr_miss 0; set cr_max 0
foreach t $cr_todo {
  lassign $t d x y nm
  set i [$ff_blk findInst $nm]
  set c0 [expr {int(round(double($ff_x1 - 21 * $ff_sw - $x) / $cr_cp))}]; set r0 [expr {int(round(double($y - $ff_y0) / $cr_rp))}]
  set done 0
  for {set rad 0} {$rad < 400 && !$done} {incr rad} {
    for {set dr [expr {-$rad}]} {$dr <= $rad && !$done} {incr dr} {
      foreach dc [lsort -unique [list [expr {$rad - abs($dr)}] [expr {abs($dr) - $rad}]]] {
        set c [expr {$c0 + $dc}]; set r [expr {$r0 + $dr}]
        if {$c < 0 || $r < 0 || $c >= $cr_ncol || $r >= $cr_nrow || [dict exists $cr_occ "$c,$r"]} continue
        dict set cr_occ "$c,$r" 1
        set cx [expr {$ff_x0 + ($cr_c0 - $c * 40) * $ff_sw}]; set cy [expr {$ff_y0 + $r * $cr_rp}]
        # a wider flop (DFFASR is 30 sites) must stay inside the core at the E edge
        set cx [expr {min($cx, $ff_x1 - [[$i getMaster] getWidth])}]
        $i setPlacementStatus PLACED
        if {[dict exists $ff_orient $cy]} { $i setOrient [dict get $ff_orient $cy] }
        $i setLocation $cx $cy
        $i setPlacementStatus FIRM
        set dm [expr {abs($cx - $x) + abs($cy - $y)}]; if {$dm > $cr_max} { set cr_max $dm }
        incr cr_n; set done 1; break
      }
    }
  }
  if {!$done} { incr cr_miss }
}
puts "OT_CORNER_RELIEF moved $cr_n of [llength $cr_todo] face flops in the SE window ([expr {$cr_w/double($ff_dbu)}] x [expr {$cr_h/double($ff_dbu)}] um, grid $cr_ncol x $cr_nrow), max move [expr {$cr_max/double($ff_dbu)}] um, missing $cr_miss"
if {$cr_miss} { error "OT_CORNER_RELIEF: $cr_miss flops found no site" }
