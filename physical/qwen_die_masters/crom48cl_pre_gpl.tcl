# PRE_GLOBAL_PLACE hook for qfd_crom48 "-cl" (drive-0158): three anchors, placement only (netlist unchanged).
#  1. rom_cap_at_pins.tcl: every ROM rd_out capture flop (e4) at its macro pin.
#  2. out_flop_at_pins.tcl: every output port's launching flop (e6 q_p with OREG=1) at its pin (lane window).
#  3. the SELECT BAND: the e5 output stations q_r[l*64+b] and the e2 decode flops g_dec[l].{tv,tk,tr,trng,tal} FIRM in
#     the band between the two macro halves (y = OT_BAND_Y0 .. OT_BAND_Y1, default 492 .. 538 um), inside lane l's
#     pin window (x = 12.15 l .. 12.15 (l+1)).  Every macro is then <= ~480 um from the band and the band <= ~520 um
#     from the N face.  crom48cl_release.tcl (PRE_DETAIL_PLACE) returns all of them to PLACED for DPL.
source $::env(QDM_SDC_DIR)/rom_cap_at_pins.tcl
source $::env(QDM_SDC_DIR)/out_flop_at_pins.tcl
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_y0 [expr {[info exists ::env(OT_BAND_Y0)] ? $::env(OT_BAND_Y0) : 492.0}]
set ot_y1 [expr {[info exists ::env(OT_BAND_Y1)] ? $::env(OT_BAND_Y1) : 538.0}]
set ot_win 12.15
array set ot_lane {}
foreach i [$ot_blk getInsts] {
  if {[[$i getMaster] isBlock]} continue
  if {![string match "DFF*" [[$i getMaster] getName]]} continue
  if {[$i getPlacementStatus] eq "FIRM"} continue
  set nm [$i getName]
  if {[regexp {^q_r\\?\[([0-9]+)\\?\]} $nm -> b]} { lappend ot_lane([expr {$b / 64}]) $i; continue }
  if {[regexp {g_dec\\?\[([0-9]+)\\?\]\.(tv|tk|tr|trng|tal)} $nm -> l]} { lappend ot_lane($l) $i }
}
set ot_band {}
foreach l [array names ot_lane] {
  set fl $ot_lane($l)
  set w [expr {double([[[lindex $fl 0] getMaster] getWidth]) / $ot_dbu + 0.25}]
  set h [expr {double([[[lindex $fl 0] getMaster] getHeight]) / $ot_dbu}]
  set ncol [expr {max(1, int(($ot_win - 0.5) / $w))}]
  set nrow [expr {int(ceil(double([llength $fl]) / $ncol))}]
  set dy [expr {max($h, ($ot_y1 - $ot_y0 - $h) / max(1, $nrow))}]
  set ot_cromcl_band_index 0
  foreach i $fl {
    set x [expr {$l * $ot_win + 0.25 + ($ot_cromcl_band_index % $ncol) * $w}]
    set y [expr {$ot_y0 + ($ot_cromcl_band_index / $ncol) * $dy}]
    $i setLocation [expr {round($x * $ot_dbu)}] [expr {round($y * $ot_dbu)}]
    $i setPlacementStatus FIRM
    lappend ot_band [$i getName]
    incr ot_cromcl_band_index
  }
}
set fh [open $::env(RESULTS_DIR)/ot_crom48cl_band.txt w]
foreach n $ot_band { puts $fh $n }
close $fh
puts "OT_CROMCL band: [llength $ot_band] select/decode flops fixed in y $ot_y0..$ot_y1 over [array size ot_lane] lane windows"
if {[llength $ot_band] < 4096} { error "OT_CROMCL: only [llength $ot_band] band flops found (expect >= 4096 q_r); netlist names changed?" }
