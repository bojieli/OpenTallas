# A0 rc10 / REGROOT 9 (QW-CB16A0-2 10-20): LANDED crossings (rtl/physical/ot_qw_land4.sv, LANDING-CONTRACT L1-L7).
# Every ring cell (u_qlw*) -> read cell (u_qlr*) path is a fixed-calendar multicycle path: the read samples a slot K = 2
# edges after it was written and the slot is not rewritten for D = 4 edges, so setup E = K = 2, hold D - 1 = 3
# (window (E - D) T + t_hold < dL < E T - t_cq - t_setup, i.e. |dL| up to ~1.5 ns between the two roots).
set ot_qland_from [get_cells -quiet *u_qlw*]
set ot_qland_to   [get_cells -quiet *u_qlr*]
if {[llength $ot_qland_from] > 0 && [llength $ot_qland_to] > 0} {
  set_multicycle_path -setup 2 -from $ot_qland_from -to $ot_qland_to
  set_multicycle_path -hold 3 -from $ot_qland_from -to $ot_qland_to
}
puts "OT_QLAND_SDC from [llength $ot_qland_from] to [llength $ot_qland_to] cells"
