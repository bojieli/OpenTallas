foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_TT_*.lib*]] {read_liberty $f}
set R /work/run/results/asap7/hc_ot_s81c_attn_hcore_swr/base
read_db $R/5_1_grt.odb
read_sdc $R/5_1_grt.sdc
set_clock_latency -source 258.53 [get_clocks vclk]
set sta_recovery_removal_checks_enabled 1
set_propagated_clock [get_clocks clk]
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
puts "HCORE_CAP24_TT hold_ps [sta::time_sta_ui [sta::worst_slack_cmd min]] nhold [sta::endpoint_violation_count min] setup_ps [sta::time_sta_ui [sta::worst_slack_cmd max]] nsetup [sta::endpoint_violation_count max]"
report_checks -path_delay max -group_path_count 3 -fields {fanout cap slew} -format full_clock_expanded > /work/cap24_tt_native_worst.rpt
report_checks -path_delay min -group_path_count 3 -fields {fanout cap slew} -format full_clock_expanded > /work/cap24_tt_native_hold.rpt
