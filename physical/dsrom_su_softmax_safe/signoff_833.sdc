# SAFE tile sign-off clock: 833.333 ps, SS setup 60 / FF hold 25 ps (read by tools/w18/corner_sta.py --post-sdc). IO is
# false-pathed here and checked by check_io.sh against the measured insertion.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
set_false_path -from [all_inputs -no_clocks]
set_false_path -to [all_outputs]
