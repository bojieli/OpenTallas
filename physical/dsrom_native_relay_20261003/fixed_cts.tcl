set_clock_transition 20 [get_clocks core_clk]
set_propagated_clock [all_clocks]
check_placement -verbose
estimate_parasitics -placement
report_metrics 4 "native fixed clock tree"
orfs_write_db $::env(RESULTS_DIR)/4_1_cts.odb
orfs_write_sdc $::env(RESULTS_DIR)/4_cts.sdc
exit
