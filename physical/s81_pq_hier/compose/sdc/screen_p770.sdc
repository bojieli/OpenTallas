# PQ screen composition route SDC (770 ps route target, as die_p770.sdc) with the vclk IO of io_vclk.sdc.
create_clock -name core_clk -period 770 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_max_fanout 32 [current_design]
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_max_transition 260 [current_design]
source $::env(QDM_SDC_DIR)/io_vclk.sdc
