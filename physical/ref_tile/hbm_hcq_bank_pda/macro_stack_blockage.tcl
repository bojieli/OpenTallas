# HBMb/HC-BANK 10-21 (PD-AUDIT 4b): abutted SRAM pairs (g_w stacks at 70.512 um pitch, 0.024 um gaps) are one
# macro stack: a hard placement blockage covers every macro-macro gap narrower than OT_STACK_CHANNEL_UM (21.6) between
# two hard SRAM macros that overlap in the other axis, extended by the macro halo, so no placement row survives in a
# sliver channel (textbook_lint util_channel "block the channel").  Macros / outline / pins are unchanged.
set ot_sb_block [ord::get_db_block]
set ot_sb_dbu [$ot_sb_block getDbUnitsPerMicron]
set ot_sb_min [expr {[info exists ::env(OT_STACK_CHANNEL_UM)] ? $::env(OT_STACK_CHANNEL_UM) : 21.6}]
set ot_sb_halo 5.4
set ot_sb_boxes {}
foreach ot_sb_i [$ot_sb_block getInsts] {
  set ot_sb_m [$ot_sb_i getMaster]
  if {![$ot_sb_m isBlock] || ![string match ot_sram_* [$ot_sb_m getName]]} continue
  set ot_sb_b [$ot_sb_i getBBox]
  lappend ot_sb_boxes [list [$ot_sb_i getName] [expr {[$ot_sb_b xMin]/double($ot_sb_dbu)}] [expr {[$ot_sb_b yMin]/double($ot_sb_dbu)}] \
                         [expr {[$ot_sb_b xMax]/double($ot_sb_dbu)}] [expr {[$ot_sb_b yMax]/double($ot_sb_dbu)}]]
}
set ot_sb_n 0
foreach a $ot_sb_boxes {
  lassign $a an ax0 ay0 ax1 ay1
  foreach b $ot_sb_boxes {
    lassign $b bn bx0 by0 bx1 by1
    if {$an eq $bn} continue
    # vertical gap: b above a, overlapping in x
    set ox0 [expr {max($ax0, $bx0)}]; set ox1 [expr {min($ax1, $bx1)}]
    set g [expr {$by0 - $ay1}]
    if {$ox1 > $ox0 && $g >= 0 && $g < $ot_sb_min} {
      set r [list [expr {min($ax0,$bx0) - $ot_sb_halo}] [expr {$ay1 - $ot_sb_halo}] [expr {max($ax1,$bx1) + $ot_sb_halo}] [expr {$by0 + $ot_sb_halo}]]
      odb::dbBlockage_create $ot_sb_block {*}[lmap v $r {expr {int(round($v * $ot_sb_dbu))}}]
      incr ot_sb_n
      puts "OT_STACK_BLOCKAGE $an|$bn gap [format %.3f $g] um -> hard blockage $r"
    }
    # horizontal gap: b right of a, overlapping in y
    set oy0 [expr {max($ay0, $by0)}]; set oy1 [expr {min($ay1, $by1)}]
    set g [expr {$bx0 - $ax1}]
    if {$oy1 > $oy0 && $g >= 0 && $g < $ot_sb_min} {
      set r [list [expr {$ax1 - $ot_sb_halo}] [expr {min($ay0,$by0) - $ot_sb_halo}] [expr {$bx0 + $ot_sb_halo}] [expr {max($ay1,$by1) + $ot_sb_halo}]]
      odb::dbBlockage_create $ot_sb_block {*}[lmap v $r {expr {int(round($v * $ot_sb_dbu))}}]
      incr ot_sb_n
      puts "OT_STACK_BLOCKAGE $an|$bn gap [format %.3f $g] um -> hard blockage $r"
    }
  }
}
puts "OT_STACK_BLOCKAGE $ot_sb_n sliver channel(s) blocked (< $ot_sb_min um)"
