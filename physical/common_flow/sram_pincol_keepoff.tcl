# QC-SU-SRAMHALO (2026-10-27, COORD 05:4x): PRE_GLOBAL_ROUTE M2-M5 ROUTING keep-off at every hard-macro corner where a
# pin column meets the macro top/bottom edge.  Shared form of the QC-SU-BTAB-R5 hook (GEOM-REVIEW-7 PASS, btab r5 DRT 0
# at it 11; r4 residue sat at the NE SRAM corner, prog L2 residue (55 markers) at the NE corner of SRAM band 2): with the
# std-cell exclusion strips of gen_core_kit_qc.py (sram_pincol_halo.json) it is ONE structural fix for both.
# Per macro edge that carries signal pins (W/E faces): an L-shaped box pair per corner
#   (a) outside the face: OT_PCH_CKO_X (1.08) wide, from OT_PCH_CKO_IN (0.30) inside the macro edge to OT_PCH_CKO_Y (2.16)
#       into the gap, layers M2-M5;
#   (b) over the macro corner: same y span, OT_PCH_CKO_X inside the face, M5 only (M2-M4 are macro OBS already).
# Nets crossing the gap therefore enter it >= OT_PCH_CKO_Y from the macro edge, nothing turns around the corner.
# Boxes overlapping a special-net (PDN) shape on their layer are skipped and reported.  No globals (may be sourced in a proc).
proc ot_pch_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
proc ot_pch_keepoff {} {
  set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]; set t [ord::get_db_tech]
  set X [expr {round([ot_pch_env OT_PCH_CKO_X 1.08] * $u)}]; set Y [expr {round([ot_pch_env OT_PCH_CKO_Y 2.16] * $u)}]
  set I [expr {round([ot_pch_env OT_PCH_CKO_IN 0.30] * $u)}]
  set pg {}
  foreach n [$b getNets] {
    if {![$n isSpecial]} continue
    foreach sw [$n getSWires] { foreach w [$sw getWires] { if {![$w isVia]} { lappend pg [list [[$w getTechLayer] getName] [$w xMin] [$w yMin] [$w xMax] [$w yMax]] } } }
  }
  set n 0; set s 0; set f [open $::env(RESULTS_DIR)/sram_pincol_keepoff.txt w]
  foreach i [$b getInsts] {
    if {![[$i getMaster] isBlock]} continue
    set bb [$i getBBox]; set X0 [$bb xMin]; set X1 [$bb xMax]; set Y0 [$bb yMin]; set Y1 [$bb yMax]
    # faces that carry signal pins (instance frame)
    set faces {}
    foreach it [$i getITerms] {
      if {[$it getNet] eq "NULL" || [[$it getNet] getSigType] in {POWER GROUND}} continue
      set r [$it getBBox]
      if {[$r xMin] - $X0 < $u / 10} { lappend faces W } elseif {$X1 - [$r xMax] < $u / 10} { lappend faces E }
    }
    foreach side [lsort -unique $faces] {
      foreach end {S N} {
        set ya [expr {$end eq "N" ? $Y1 - $I : $Y0 - $Y}]; set yb [expr {$end eq "N" ? $Y1 + $Y : $Y0 + $I}]
        set out [expr {$side eq "E" ? [list $X1 [expr {$X1 + $X}]] : [list [expr {$X0 - $X}] $X0]}]
        set ins [expr {$side eq "E" ? [list [expr {$X1 - $X}] $X1] : [list $X0 [expr {$X0 + $X}]]}]
        foreach lay {M2 M3 M4 M5} {
          foreach part {out ins} {
            if {$part eq "ins" && $lay ne "M5"} continue
            lassign [set $part] xa xb; set hit 0
            foreach p $pg { lassign $p l a c d e; if {$l eq $lay && $a < $xb && $d > $xa && $c < $yb && $e > $ya} { set hit 1; break } }
            if {$hit} { incr s; puts $f "SKIP_PG [$i getName] $side$end $lay $part"; continue }
            odb::dbObstruction_create $b [$t findLayer $lay] $xa $ya $xb $yb; incr n
            puts $f [format "KEEPOFF %s %s%s %s %s %.3f %.3f %.3f %.3f" [$i getName] $end $side $lay $part \
              [expr {$xa / double($u)}] [expr {$ya / double($u)}] [expr {$xb / double($u)}] [expr {$yb / double($u)}]]
          }
        }
      }
    }
  }
  close $f
  puts "SRAM_PINCOL_KEEPOFF $n routing obstructions (M2-M5) at macro pin-face corners, $s skipped for PDN overlap"
}
ot_pch_keepoff
