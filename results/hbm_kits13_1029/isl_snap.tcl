# HBM-CORES-KITS-13: mp_isl* ft pins off the M5 track grid (x_offset 0.024 pitch 0.048) -> DRT-0255 on mp_isl0_ck_o
# (m10 DRT 07:10). Snap each off-track M5 BPin box to the nearest track (shape kept), write back. Plan delta reported.
read_db $::env(ODB_IN)
set b [ord::get_db_block]
set n 0
foreach t [$b getBTerms] {
  if {![string match mp_isl* [$t getName]]} continue
  foreach p [$t getBPins] {
    foreach x [$p getBoxes] {
      set L [$x getTechLayer]; if {[$L getName] ne "M5"} continue
      set x1 [$x xMin]; set x2 [$x xMax]; set y1 [$x yMin]; set y2 [$x yMax]
      set c [expr {($x1 + $x2) / 2}]; set k [expr {round(($c - 24) / 48.0)}]; set ct [expr {24 + 48 * $k}]
      if {$ct == $c} continue
      set d [expr {$ct - $c}]
      odb::dbBox_destroy $x
      odb::dbBox_create $p $L [expr {$x1 + $d}] $y1 [expr {$x2 + $d}] $y2
      puts "ISL_SNAP [$t getName] x $c -> $ct (d $d nm)"; incr n
    }
  }
}
puts "ISL_SNAP_COUNT $n"
write_db $::env(ODB_OUT)
