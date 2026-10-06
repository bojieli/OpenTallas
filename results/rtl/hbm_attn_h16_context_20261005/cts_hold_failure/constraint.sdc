set clk_period 833.333
create_clock -name core_clk -period $clk_period [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_max_fanout 32 [current_design]
set_clock_latency -source 0 [get_clocks core_clk]
set_clock_latency -min 90 [get_clocks core_clk]
set_clock_latency -max 100 [get_clocks core_clk]
set ot_inputs [all_inputs -no_clocks]
set_input_delay -clock core_clk -max 166.6666666666667 $ot_inputs
set_input_delay -clock core_clk -min 0 $ot_inputs
set_output_delay -clock core_clk -max 166.6666666666667 [all_outputs]
set_output_delay -clock core_clk -min 0 [all_outputs]
set_load 9.673192 [all_outputs]
