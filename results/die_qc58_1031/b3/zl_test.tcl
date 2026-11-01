foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_TT_nldm_*] { read_liberty $f }
foreach f [glob /work/macros/*_tt.lib] { read_liberty $f }
read_db $::env(ODB)
read_sdc $::env(SDC)
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set ::env(OT_ZL_PAT) {u_g.u_tile.u_tile.u_logic.u_me.g_hier.g_sl*.g_hd.g_tx.g_r*.u_tx/q*}
set ::env(OT_ZL_TT_PS) $::env(ZLT)
report_worst_slack -min
source /b3/ot_zl_pad.tcl
set t0 [clock seconds]
ot_zl_pad
puts "ZL took [expr {[clock seconds]-$t0}] s"
report_worst_slack -min
report_worst_slack -max
