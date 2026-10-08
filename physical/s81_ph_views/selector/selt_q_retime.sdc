# Reset release already reserves two edges at every selector tile. Match nested
# q2.u_q reset synchronizer, which the legacy top-level-only pattern missed.
set ot_qrst {}
foreach ot_c [get_cells *] {
  if {[regexp {(^|[./])rst_s\\?\[1\\?\]} [get_full_name $ot_c]]} { lappend ot_qrst $ot_c }
}
if {[llength $ot_qrst]} {
  set_multicycle_path -setup 2 -from $ot_qrst
  set_multicycle_path -hold 1 -from $ot_qrst
}
puts "OT_SELT_Q_RETIME nested reset sources [llength $ot_qrst]"
