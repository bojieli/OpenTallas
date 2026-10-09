# ot_hcoll_port2 slice macro placement (stream coll-fallback, 2026-10-08; MACRO_PLACEMENT_TCL via route_ps.sh MPT).
# The 8-slice ot_hcoll_port failed GRT-0116 with the SRAMs ringed on the die edge (pins and q buses crossing macros on
# M6, the only horizontal layer over an SRAM).  Here every hard macro sits in ROWS of OT_MR_NCOL (3) with vertical
# gaps of OT_MR_GAPX um (the SRAM pins are M4 on its left / right faces, ~410 a face) and the rows spread over the full
# height, so each pair of rows has a wide HORIZONTAL channel (~37 um at 940 um); no macro touches a pin edge (core
# side pins on the top edge, PHY pins on the bottom: vertical M3/M5 flow down the gaps and over the macros).
# Macros are taken in name order (lsort -dictionary): half g_h[0] fills the bottom rows, g_h[1] the top rows; within a
# half one 545-bit word (3 macros) is one row: qp, qr, rb bank 0/1, wrx, wtx.  R0 only (no mirrored macros: track
# alignment), origins on a 0.432 um grid.
set ncol [expr {[info exists ::env(OT_MR_NCOL)] ? $::env(OT_MR_NCOL) : 3}]
set gapx [expr {[info exists ::env(OT_MR_GAPX)] ? $::env(OT_MR_GAPX) : 20.0}]
set my   [expr {[info exists ::env(OT_MR_MARGIN_Y)] ? $::env(OT_MR_MARGIN_Y) : 16.0}]
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set die [$block getDieArea]
set W [expr {double([$die xMax] - [$die xMin]) / $dbu}]
set H [expr {double([$die yMax] - [$die yMin]) / $dbu}]
set names {}
foreach inst [$block getInsts] {
  if {[[$inst getMaster] isBlock]} { lappend names [$inst getName] }
}
set names [lsort -dictionary $names]
set n [llength $names]
if {$n == 0} { error "macro_rows.tcl: no hard macros" }
set m0 [[$block findInst [lindex $names 0]] getMaster]
set mw [expr {double([$m0 getWidth]) / $dbu}]
set mh [expr {double([$m0 getHeight]) / $dbu}]
set nrow [expr {($n + $ncol - 1) / $ncol}]
proc snap {v} { return [expr {floor($v / 0.432) * 0.432}] }
set rw [expr {$ncol * $mw + ($ncol - 1) * $gapx}]
set x0 [snap [expr {($W - $rw) / 2.0}]]
set pitch [expr {$nrow > 1 ? ($H - 2.0 * $my - $mh) / ($nrow - 1) : 0.0}]
if {$x0 < 2.0 || $pitch < $mh + 4.0} { error "macro_rows.tcl: $n macros ($ncol a row) do not fit ${W}x${H}" }
puts "macro_rows.tcl: $n macros, $nrow rows of $ncol, die ${W}x${H}, x0 $x0, gap x $gapx, row pitch $pitch (channel [expr {$pitch - $mh}])"
set i 0
foreach name $names {
  set r [expr {$i / $ncol}]
  set c [expr {$i % $ncol}]
  set x [snap [expr {$x0 + $c * ($mw + $gapx)}]]
  set y [snap [expr {$my + $r * $pitch}]]
  # placed through ODB (place_macro's name pattern lookup failed on the generate-index brackets: MPL-0020)
  set inst [$block findInst $name]
  $inst setOrient R0
  $inst setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]
  $inst setPlacementStatus FIRM
  incr i
}
# FIRM: rtl_macro_placer (run after this file by macro_place_util.tcl) keeps them
foreach inst [$block getInsts] {
  if {[[$inst getMaster] isBlock]} { $inst setPlacementStatus FIRM }
}
puts "OT_MACRO_ROWS_PLACED macros=$n"
