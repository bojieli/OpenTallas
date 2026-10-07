# Original full-IO contract at target frequency; reset remains the route's exception.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
set_input_delay -max 166.6666 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max 166.6666 -clock core_clk [all_outputs]
