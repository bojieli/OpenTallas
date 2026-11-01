
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_TT_nldm_*] { read_liberty $f }
foreach f [glob /work/macros/*_tt.lib] { read_liberty $f }
read_db /work/probe_in.odb
read_sdc /work/probe_in.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
puts "CODEX BEFORE"
report_worst_slack -min
report_worst_slack -max
set ::env(OT_B3_ICG) g_icg.g_root.u_icg
set ::env(OT_B3_EARLY) {}
set ::env(OT_B3_MID) {}
set ::env(OT_B3_SWAP) $::env(SWAP)
source /work/b3_early.tcl
if {$::env(SWAP)} { ot_b3_early_branch }
set ::env(OT_ZL_PAT) {u_g.u_tile.u_tile.u_logic.u_me.g_hier.g_sl*.g_hd.g_tx.g_r*.u_tx/q*}
set ::env(OT_ZL_TT_PS) 40
set ::env(OT_ZL_MAX) 16
source /work/ot_zl_pad.tcl
ot_zl_pad
estimate_parasitics -placement
puts "CODEX AFTER"
report_worst_slack -min
report_worst_slack -max
report_checks -path_delay max -to [get_pins g_icg.g_root.u_icg/ENA] -group_path_count 3 -endpoint_path_count 3 -fields {cap slew fanout} -digits 2
write_db /work/z$::env(SWAP).odb
