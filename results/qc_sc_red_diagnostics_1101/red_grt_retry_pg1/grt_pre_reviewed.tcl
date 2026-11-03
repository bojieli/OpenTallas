source /work/grt_pre_core.tcl
source /work/clk_freeze.tcl
file mkdir $::env(RESULTS_DIR)/red_clock_freeze
ot_clk_freeze $::env(RESULTS_DIR)/red_clock_freeze
source /work/red_ff_master_preserve.tcl
