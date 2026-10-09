# MACRO_PLACEMENT_TCL for qfd_crom48 "-cl" (drive-0158, REVIEW_20261009 addendum 02:35): BANKED-COLUMN map + select band.
# Lanes 16c..16c+15 (pin windows x = 194.4c .. 194.4(c+1) on the N face) read wide columns 4c..4c+3 and narrow
# columns 2c, 2c+1: exactly 12 macros, all placed in physical column c (x = 12.96 + 190c), so the lane -> source
# distance is vertical only.  Rows: 6 above a ~50 um select band (y ~ 490..540), 6 below; row pitch 76 um (13.1 um
# gaps >= the 12 um sliver rule).  Top row 15 um off the N pin face.  Order inside a column (top -> bottom):
#   w(4c+0) d0, d1, w(4c+1) d0, d1, n(2c) d0, d1 | band | w(4c+2) d0, d1, w(4c+3) d0, d1, n(2c+1) d0, d1
# Names come from OpenDB (escaping differs between synthesis and the linked DB), parsed, never guessed.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_fh [expr {double([[$ot_blk getDieArea] yMax]) / $ot_dbu}]
set ot_pitch 76.0; set ot_mh 62.91; set ot_top_gap 15.0; set ot_band 50.0
set ot_n 0
foreach m [$ot_blk getInsts] {
  if {!([[$m getMaster] isBlock] && [[$m getMaster] getName] eq "ot_rom_4096x266_m8")} continue
  set nm [$m getName]
  if {![regexp {g_([wn])\\?\[([0-9]+)\\?\]\.g_d\\?\[([0-9]+)\\?\]} $nm -> kind col dep]} { error "CROM48CL: cannot parse macro name $nm" }
  if {$kind eq "w"} { set c [expr {$col / 4}]; set k [expr {$col % 4}]; set slot [expr {($k % 2) * 2 + $dep}]; set half [expr {$k / 2}] } \
  else { set c [expr {$col / 2}]; set k [expr {$col % 2}]; set slot [expr {4 + $dep}]; set half $k }
  # half 0 = above the band (row index from the top), half 1 = below
  if {$half == 0} { set y [expr {$ot_fh - 2.16 - $ot_top_gap - $ot_mh - $slot * $ot_pitch}] } \
  else { set y [expr {$ot_fh - 2.16 - $ot_top_gap - $ot_mh - 5 * $ot_pitch - $ot_mh - $ot_band - $slot * $ot_pitch}] }
  set x [expr {12.96 + $c * 190.0}]
  $m setOrient R0
  $m setLocation [expr {round($x * $ot_dbu)}] [expr {round($y * $ot_dbu)}]
  $m setPlacementStatus FIRM
  puts "CROM48CL macro $nm col $c half $half slot $slot at $x $y"
  incr ot_n
}
if {$ot_n != 48} { error "CROM48CL requires 48 real macros; found $ot_n" }
