# el1011-q-coll 2026-10-11 (MACRO_PLACEMENT_TCL): qfd_io_host_qm KV corner-turn macros (2 x 16 ot_sram_1r1w_32x128_m1).
# The ORFS auto placer put banks against pin edges (FLOORPLAN_MARGIN macro_edge, hing_qfd_qm-2e9dedd38).  Planned grid:
# 4 columns x 8 rows centred in the core -- columns 0-1 the K banks (u_mk), columns 2-3 the V banks (u_mv), bank b in
# row b mod 8 of column b / 8 of its pair -- with 20 um channels; the whole array keeps >= ~80 um from every core edge
# for the pin-side logic.  x snapped to 0.216 um, y to the 0.27 um row grid.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_core [$ot_blk getCoreArea]
set cx0 [expr {double([$ot_core xMin]) / $ot_dbu}]; set cx1 [expr {double([$ot_core xMax]) / $ot_dbu}]
set cy0 [expr {double([$ot_core yMin]) / $ot_dbu}]; set cy1 [expr {double([$ot_core yMax]) / $ot_dbu}]
set mw 51.41; set mh 20.79; set ch 20.0
set gw [expr {4 * $mw + 3 * $ch}]; set gh [expr {8 * $mh + 7 * $ch}]
set gx [expr {($cx0 + $cx1 - $gw) / 2.0}]; set gy [expr {($cy0 + $cy1 - $gh) / 2.0}]
puts "OT_QMP core [format %.1f [expr {$cx1-$cx0}]] x [format %.1f [expr {$cy1-$cy0}]] grid [format %.1f $gw] x [format %.1f $gh] at [format %.1f $gx] [format %.1f $gy]"
if {$gx - $cx0 < 40 || $gy - $cy0 < 40} { puts "OT_QMP ERROR: core too small for the planned bank grid"; exit 1 }
set n 0
foreach i [$ot_blk getInsts] {
  if {[[$i getMaster] getName] ne "ot_sram_1r1w_32x128_m1"} continue
  set nm [$i getName]
  if {![regexp {g_mb\\?\[(\d+)\\?\]\.u_m([kv])} $nm -> b kv]} { puts "OT_QMP ERROR: unexpected macro $nm"; exit 1 }
  set col [expr {($kv eq "k" ? 0 : 2) + $b / 8}]; set row [expr {$b % 8}]
  set x [expr {round(($gx + $col * ($mw + $ch)) / 0.216) * 0.216}]
  set y [expr {round(($gy + $row * ($mh + $ch)) / 0.27) * 0.27}]
  place_macro -macro_name $nm -location [list $x $y] -orientation R0
  incr n
}
if {$n != 32} { puts "OT_QMP ERROR: placed $n of 32 bank macros"; exit 1 }
puts "OT_QMP placed $n bank macros"
