# el1011-ds-vm/be 2026-10-11 (tools/s81_ph/s81_ph_vm_be_v3.py): the 4 BE v3 slice tiles dsfd_vm_be_sl, tile s at
# x = s * 388.8 + 43.2, y = 21.6 (R0, fixed); channels: 86.4 um between tiles, 21.60 um N, 21.6 um S.
set ot_blk [ord::get_db_block]
set ot_u [$ot_blk getDbUnitsPerMicron]
foreach ot_i [$ot_blk getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_s\\?\[(\d+)\\?\]\.u_sl$} $ot_nm -> ot_s]} { continue }
  set ot_x [expr {round(($ot_s * 388.8 + 43.2) * $ot_u)}]
  set ot_y [expr {round(21.6 * $ot_u)}]
  $ot_i setOrient R0
  $ot_i setLocation $ot_x $ot_y
  $ot_i setPlacementStatus FIRM
  puts "OT_BE_V3 placed $ot_nm at [expr {$ot_x / double($ot_u)}] [expr {$ot_y / double($ot_u)}]"
}
