# Private diagnostic source clock. No production-parent timing claim.
create_clock -name core_clk -period 770 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_input_delay 100 -clock core_clk [all_inputs -no_clocks]
set_output_delay 100 -clock core_clk [all_outputs]
set_load 80 [all_outputs]
set_max_fanout 32 [current_design]
