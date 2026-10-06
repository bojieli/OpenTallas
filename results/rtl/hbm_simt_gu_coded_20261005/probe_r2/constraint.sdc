create_clock -name core_clk -period 833 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_ports rst_n]
set ins [get_ports {we next_data*}]
set_input_delay -max 300 -clock core_clk $ins
set_input_delay -min 30 -clock core_clk $ins
set_output_delay -max 300 -clock core_clk [all_outputs]
set_output_delay -min 50 -clock core_clk [all_outputs]
set_load 2.0 [all_outputs]
set_max_fanout 32 [current_design]
