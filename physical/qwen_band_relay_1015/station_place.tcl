# q15 r13 BAND relay: PRE_GLOBAL_PLACE (pin_hook_before_flops) -- every station flop FIRM in its planned block
# (station_table.tcl: lane.group.stage -> block lower-left; 16 columns x 1.296 um, rows of one site row), so the relay
# hop lengths are the planned ones (<= 666 um) instead of whatever a wirelength placer picks on a straight line.  The
# flops are released after global placement (station_release.tcl) and legalised by DPL inside their block.
source /src/physical/qwen_band_relay_1015/station_table.tcl
set ot_b [ord::get_db_block]
set ot_dbu [$ot_b getDbUnitsPerMicron]
set ot_row [lindex [$ot_b getRows] 0]
set ot_site [$ot_row getSite]
set ot_sw [$ot_site getWidth]; set ot_sh [$ot_site getHeight]
set ot_core [$ot_b getCoreArea]; set ot_cx [$ot_core xMin]; set ot_cy [$ot_core yMin]
set ot_gmap [dict create tw TW ty TY tt TT c CP pw CP st S]
set ot_n 0; set ot_miss 0; set ::ot_band_firm {}
foreach i [$ot_b getInsts] {
  set nm [string map {\\ {}} [$i getName]]
  if {![regexp {g_lane\[(\d+)\]\.(tw|ty|tt|c|pw|st)_s([12])\[(\d+)\]} $nm -> l g s bit]} continue
  if {![[$i getMaster] isSequential]} continue
  set key "$l.[dict get $ot_gmap $g].$s"
  if {![dict exists $::ot_band_st $key]} { incr ot_miss; continue }
  if {$g eq "pw"} { set bit [expr {$bit + 26}] }
  lassign [dict get $::ot_band_st $key] bx by
  set x [expr {int(round(($bx + ($bit % 16) * 1.296) * $ot_dbu))}]
  set y [expr {int(round($by * $ot_dbu)) + ($bit / 16) * $ot_sh}]
  set x [expr {$ot_cx + (($x - $ot_cx) / $ot_sw) * $ot_sw}]
  set y [expr {$ot_cy + (($y - $ot_cy) / $ot_sh) * $ot_sh}]
  $i setLocation $x $y
  $i setPlacementStatus FIRM
  lappend ::ot_band_firm $i
  incr ot_n
}
puts "OT_BAND_STATIONS placed $ot_n station flops FIRM ($ot_miss without a planned block)"
if {$ot_n != 16 * 2 * (256 + 256 + 98 + 58 + 8)} { error "OT_BAND_STATIONS expected [expr {16 * 2 * 676}] station flops, found $ot_n" }
