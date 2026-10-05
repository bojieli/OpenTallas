set clk_period 920
create_clock -name core_clk -period $clk_period [get_ports clk]
set_input_delay 184 -clock core_clk [all_inputs -no_clocks]
set_output_delay 184 -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_max_fanout 32 [current_design]
set_max_transition 320 [current_design]
