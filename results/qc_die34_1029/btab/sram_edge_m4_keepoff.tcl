# DIE-QC-34 BTAB QC-014 (COORD ruling 2026-10-29 10:09, V1/V2): PRE_GLOBAL_ROUTE M4 + V4 ROUTING keep-off over the inner
# edge strip of every hard macro face that carries signal pins (W/E).  Same mechanism as sram_pincol_keepoff.tcl
# (odb::dbObstruction_create, sourced from grt_pre_core.tcl).  Root cause (F3b 6_final probe, CHECKED): std-cell nets
# run M5 over the macro, drop VIA45 1.3 um INSIDE the macro face (e.g. net4045 at x 253.404, face 254.664) and run M4
# out across the macro M4 OBS -> 4 M4 Shorts + 1 M4 spacing.  The strip starts OT_SEK_IN (0.072 = the LEF M4 OBS inset,
# pin access stays free) inside the face and ends OT_SEK_DEPTH (1.70) inside it, i.e. before the macro M5/V4 PG stripe
# (2.0-2.1 um inside).  Strips that would touch a special-net (PDN) shape on M4/V4 are trimmed away from it and reported.
proc ot_sek_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
proc ot_sek_keepoff {} {
  set b [ord::get_db_block]; set t [ord::get_db_tech]; set u [$t getDbUnitsPerMicron]
  set IN [expr {round([ot_sek_env OT_SEK_IN 0.072] * $u)}]; set D [expr {round([ot_sek_env OT_SEK_DEPTH 1.70] * $u)}]
  set SP [expr {round(0.048 * $u)}]
  set lays {}
  foreach ln {M4 V4} { set l [$t findLayer $ln]; if {$l eq "NULL" || $l eq ""} { error "OT_SEK: layer $ln missing" }; lappend lays $ln }
  set pg {}
  foreach n [$b getNets] {
    if {![$n isSpecial]} continue
    foreach sw [$n getSWires] { foreach w [$sw getWires] { lappend pg [list [$w xMin] [$w yMin] [$w xMax] [$w yMax]] } }
  }
  set f [open $::env(RESULTS_DIR)/sram_edge_m4_keepoff.txt w]; set n 0; set trim 0
  foreach i [$b getInsts] {
    if {![[$i getMaster] isBlock]} continue
    set bb [$i getBBox]; set X0 [$bb xMin]; set X1 [$bb xMax]; set Y0 [$bb yMin]; set Y1 [$bb yMax]
    set faces {}
    foreach it [$i getITerms] {
      if {[$it getNet] eq "NULL" || [[$it getNet] getSigType] in {POWER GROUND}} continue
      set r [$it getBBox]
      if {[$r xMin] - $X0 < $u / 10} { lappend faces W } elseif {$X1 - [$r xMax] < $u / 10} { lappend faces E }
    }
    foreach side [lsort -unique $faces] {
      if {$side eq "E"} { set xa [expr {$X1 - $D}]; set xb [expr {$X1 - $IN}] } else { set xa [expr {$X0 + $IN}]; set xb [expr {$X0 + $D}] }
      # trim toward the face if any PDN shape (wire or via, any layer box) intrudes in x over the macro y span
      foreach p $pg {
        lassign $p a c d e
        if {$a < $xb && $d > $xa && $c < $Y1 && $e > $Y0 && ($d - $a) < 4 * $u} {
          if {$side eq "E"} { set xa [expr {max($xa, $d + $SP)}] } else { set xb [expr {min($xb, $a - $SP)}] }
          incr trim
        }
      }
      if {$xb - $xa < $u / 10} { puts $f "SKIP [$i getName] $side strip collapsed by PDN"; continue }
      foreach ln $lays {
        odb::dbObstruction_create $b [$t findLayer $ln] $xa $Y0 $xb $Y1; incr n
        puts $f [format "KEEPOFF %s %s %s %.3f %.3f %.3f %.3f" [$i getName] $side $ln [expr {$xa / double($u)}] [expr {$Y0 / double($u)}] [expr {$xb / double($u)}] [expr {$Y1 / double($u)}]]
      }
    }
  }
  close $f
  puts "SRAM_EDGE_M4_KEEPOFF $n routing obstructions (M4+V4) on macro pin-face inner strips, $trim PDN trims"
}
ot_sek_keepoff
