# bf-hier-1011 2026-10-10 (PRE_FLOORPLAN): keep the ot_bf_hdly hold-delay cells (ahead of the column boundary registers)
# through floorplan remove_buffers, timing-driven placement unbuffering and every repair pass.
set hb {}
foreach i [[ord::get_db_block] getInsts] {
  if {[string match *u_hdly_* [$i getName]] && [string match HB*xp67* [[$i getMaster] getName]]} { lappend hb [$i getName] }
}
if {[llength $hb] == 0} { puts "OT_HDLY none" } else {
  set_dont_touch [get_cells $hb]
  puts "OT_HDLY dont_touch [llength $hb] delay cells"
}
