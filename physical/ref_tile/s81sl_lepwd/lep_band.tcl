# S81-RTLFIX 10-20 (s81sl_lepwd): ONE full-width std-cell band y 259.2..291.6 (x 2.16..473.04, 120 rows) between TX banks 2 and 3.
# Rows outside the band are removed before tapcell (place.tcl tail, ot_lep_trim_rows); here (PRE_GLOBAL_PLACE[_SKIP_IO] /
# PRE_DETAIL_PLACE) every movable std cell is owned by one INCLUSIVE native region on the band (main native_cell_fence.tcl),
# cells born later (repair / timing-driven buffers) are adopted at each later hook, and DPL can only legalise into band rows.
# No source, net, clock, supply or timing constraint is changed.
source /src/physical/dscoll_cx/native_cell_fence.tcl
set ::ot_lep_band {2.16 259.2 473.04 291.6}
proc ot_lep_movable {} {
  set names {}
  foreach i [[ord::get_db_block] getInsts] {
    if {[[$i getMaster] isBlock]} continue
    if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
    if {[$i getGroup] ne "NULL"} continue
    lappend names [$i getName]
  }
  return $names
}
set ot_lep_b [ord::get_db_block]
if {[$ot_lep_b findGroup ot_lep_band] eq "NULL"} {
  # INCLUSIVE (gate 053145: with only band rows, an EXCLUSIVE fence leaves GPL's top-level region all-fixed and the tie
  # cells -- which GPL keeps top-level -- at 'Utilization inf'; INCLUSIVE + band-only rows: every cell lands in the band)
  set ot_lep_u [[ord::get_db_tech] getDbUnitsPerMicron]
  lassign $::ot_lep_band x0 y0 x1 y1
  set ot_lep_r [odb::dbRegion_create $ot_lep_b ot_lep_band]
  $ot_lep_r setRegionType INCLUSIVE
  odb::dbBox_create $ot_lep_r [expr {round($x0*$ot_lep_u)}] [expr {round($y0*$ot_lep_u)}] [expr {round($x1*$ot_lep_u)}] [expr {round($y1*$ot_lep_u)}]
  set ot_lep_g [odb::dbGroup_create $ot_lep_r ot_lep_band]
  $ot_lep_g setType VOLTAGE_DOMAIN
  set ot_lep_n 0
  foreach nm [ot_lep_movable] { $ot_lep_g addInst [$ot_lep_b findInst $nm]; incr ot_lep_n }
  puts "LEP_BAND_CREATED INCLUSIVE cells=$ot_lep_n box=$::ot_lep_band"
} else {
  set ot_lep_new [ot_lep_movable]
  if {[llength $ot_lep_new]} { ot_native_cell_fence_add ot_lep_band $ot_lep_new }
  puts "LEP_BAND adopted=[llength $ot_lep_new]"
}
