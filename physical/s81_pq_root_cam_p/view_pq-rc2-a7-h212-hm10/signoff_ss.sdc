create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
create_clock -name vclk -period 833.333
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set_clock_latency 393 [get_clocks vclk]
set ot_in [all_inputs -no_clocks]
set_input_delay 333.5 -clock vclk $ot_in
set_output_delay 274.5 -clock vclk [all_outputs]
set_input_delay -min 32.2 -clock vclk $ot_in
set_output_delay -min 15 -clock vclk [all_outputs]
