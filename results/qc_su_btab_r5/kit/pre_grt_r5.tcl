# QC-SU-BTAB-R5 PRE_GLOBAL_ROUTE (GEOM-REVIEW-6 16:23 structural fix (1)): r4 hook unchanged (drv.tcl + M5 0.096 pin-edge
# keep-out bands), then a planned M2-M5 ROUTING keep-off at every SRAM corner where a pin column (W and E pin faces; the
# r4 DRT residue sat at the NE corner of g_btb[1]) meets the SRAM top/bottom edge.  Each keep-off is an L-shaped box pair:
#   (a) beside the pin face, outside the macro: OT_R5_CKO_X (1.08) wide, from OT_R5_CKO_IN (0.30) inside the macro edge
#       (above the last pin: LEF pins span 0.768..40.056 of 41.064) to OT_R5_CKO_Y (2.16) into the gap;
#   (b) over the macro corner itself: the same y span, OT_R5_CKO_X inside the face (M5 only; M2-M4 are macro OBS already).
# Nets that cross the inter-SRAM gap therefore enter it >= 2.16 um from the macro edge (gap-centre escapes) and nothing turns
# around the macro corner (the hook may be sourced inside an ORFS proc: no globals).  A box that would overlap a special-net (PDN) shape on its layer is skipped and reported.
source /work/pre_grt_s6b.tcl
set ckb [ord::get_db_block]; set cku [[ord::get_db_tech] getDbUnitsPerMicron]; set ckt [ord::get_db_tech]
proc ck_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set ckX [expr {round([ck_env OT_R5_CKO_X 1.08] * $cku)}]; set ckY [expr {round([ck_env OT_R5_CKO_Y 2.16] * $cku)}]
set ckI [expr {round([ck_env OT_R5_CKO_IN 0.30] * $cku)}]
set ckpg {}
foreach n [$ckb getNets] {
  if {![$n isSpecial]} continue
  foreach sw [$n getSWires] { foreach w [$sw getWires] { if {![$w isVia]} { lappend ckpg [list [[$w getTechLayer] getName] [$w xMin] [$w yMin] [$w xMax] [$w yMax]] } } }
}
proc ck_hits_pg {pg lay x0 y0 x1 y1} {
  foreach s $pg { lassign $s l a b c d; if {$l eq $lay && $a < $x1 && $c > $x0 && $b < $y1 && $d > $y0} { return 1 } }
  return 0
}
set ckn 0; set cks 0; set ckf [open $::env(RESULTS_DIR)/r5_corner_keepoff.txt w]
foreach i [$ckb getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set bb [$i getBBox]; set X0 [$bb xMin]; set X1 [$bb xMax]; set Y0 [$bb yMin]; set Y1 [$bb yMax]
  foreach side {W E} {
    foreach end {S N} {
      set ya [expr {$end eq "N" ? $Y1 - $ckI : $Y0 - $ckY}]; set yb [expr {$end eq "N" ? $Y1 + $ckY : $Y0 + $ckI}]
      set out [expr {$side eq "E" ? [list $X1 [expr {$X1 + $ckX}]] : [list [expr {$X0 - $ckX}] $X0]}]
      set ins [expr {$side eq "E" ? [list [expr {$X1 - $ckX}] $X1] : [list $X0 [expr {$X0 + $ckX}]]}]
      foreach lay {M2 M3 M4 M5} {
        foreach part {out ins} {
          if {$part eq "ins" && $lay ne "M5"} continue
          lassign [set $part] xa xb
          if {[ck_hits_pg $ckpg $lay $xa $ya $xb $yb]} { incr cks; puts $ckf "SKIP_PG [$i getName] $side$end $lay $part"; continue }
          odb::dbObstruction_create $ckb [$ckt findLayer $lay] $xa $ya $xb $yb; incr ckn
          puts $ckf [format "KEEPOFF %s %s%s %s %s %.3f %.3f %.3f %.3f" [$i getName] $end $side $lay $part [expr {$xa/double($cku)}] [expr {$ya/double($cku)}] [expr {$xb/double($cku)}] [expr {$yb/double($cku)}]]
        }
      }
    }
  }
}
close $ckf
puts "R5_CORNER_KEEPOFF $ckn routing obstructions (M2-M5) at SRAM pin-face corners, $cks skipped for PDN overlap"
