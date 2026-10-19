# Native RVT Liberty time unit 1 ps, cap unit 1 fF. No clock/reference relaxation.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.667 -clock core_clk [all_inputs -no_clocks]
set_output_delay 166.667 -clock core_clk [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_load 80 [all_outputs]
set_max_transition 260 [current_design]
set_max_fanout 32 [current_design]
# This is a bounded physical prototype. Root-referenced IO timing is diagnostic;
# parent/neighbour matched references are required separately for qualification.
