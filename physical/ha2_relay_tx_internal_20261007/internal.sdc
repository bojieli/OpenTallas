# INTERNAL-ONLY experiment. Every external data/reset/credit boundary is unqualified.
# There are no assigned virtual launch times and no false-path waivers.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_input_transition 150 [all_inputs -no_clocks]
set_load 4 [all_outputs]
