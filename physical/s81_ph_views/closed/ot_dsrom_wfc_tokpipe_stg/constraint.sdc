# CLAUDE WFC element: 1.2 GHz, SS 60 ps setup / FF 25 ps hold uncertainty, IO at 20 % of the period
create_clock -name core_clk -period 770 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set ins [lsearch -all -inline -not [all_inputs] [get_ports clk]]
# neighbours on the same die tree: IO against io_clk with the estimated insertion as source latency;
# core_clk carries the mid estimate as ideal network latency until CTS replaces it with the real tree
set_clock_latency 350 [get_clocks core_clk]
create_clock -name io_clk -period 770
set_clock_latency -source -min 140 [get_clocks io_clk]
set_clock_latency -source -max 560 [get_clocks io_clk]
set_clock_uncertainty -setup 60 [get_clocks io_clk]
set_clock_uncertainty -hold 25 [get_clocks io_clk]
set_input_delay 166.6 -clock io_clk $ins
set_output_delay 166.6 -clock io_clk [all_outputs]
set_load 2.0 [all_outputs]
set_max_fanout 32 [current_design]
set_max_transition 320 [current_design]
