# el1011-q-kvd-head 2026-10-11: macro plan of the hierarchical head tile (ot_qwen_nearhbm_head_hs).  16 ot_qkh_lane8
# sub-tiles as a 4 x 4 array (u_l8 of g_t[t]: column t % 4 = the q beat column's bit slice, row t / 4), channels
# QKH_CH um, 43.2 um off the W (clk / rst), S (inputs) and E (nb_d) pin faces; the K-tree tile ot_qkh_ktree centred in
# the S band below the array, 43.2 um off the S face (its partials come down the channels, its score leaves on S).
# R0 only (mirrored masters put pins off track).  Positions snap to 1.08 um.  Sizes from the env (QKH_SW / QKH_KW / QKH_KH).
set b [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set sw $::env(QKH_SW); set kw $::env(QKH_KW); set kh $::env(QKH_KH); set ch $::env(QKH_CH); set mg 43.2
set core [$b getCoreArea]
set cx0 [expr {[$core xMin] / double($u)}]; set cy0 [expr {[$core yMin] / double($u)}]
set cx1 [expr {[$core xMax] / double($u)}]
set n 0
foreach m [$b getInsts] {
  set mn [[$m getMaster] getName]
  if {![[$m getMaster] isBlock]} continue
  set nm [$m getName]
  if {$mn eq "ot_qkh_ktree"} {
    set x [expr {1.08 * round((($cx0 + $cx1) / 2.0 - $kw / 2.0) / 1.08)}]
    set y [expr {1.08 * round(($cy0 + $mg) / 1.08)}]
  } elseif {$mn eq "ot_qkh_lane8"} {
    if {![regexp {g_t\.?\[?(\d+)} $nm -> t]} { error "qkh_head_place: no sub-tile index in $nm" }
    set x [expr {1.08 * round(($cx0 + $mg + ($t % 4) * ($sw + $ch)) / 1.08)}]
    set y [expr {1.08 * round(($cy0 + $mg + $kh + $ch + ($t / 4) * ($sw + $ch)) / 1.08)}]
  } else { error "qkh_head_place: unexpected macro $mn ($nm)" }
  $m setOrient R0
  $m setLocation [expr {round($x * $u)}] [expr {round($y * $u)}]
  $m setPlacementStatus FIRM
  puts "qkh_head_place: $nm ($mn) at $x $y"
  incr n
}
if {$n != 17} { error "qkh_head_place: expected 17 macros, placed $n" }
