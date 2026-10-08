# HBM SU c12 vehicle sign-off at 833.333 ps (OWNER RULE 2026-10-06: route at 770, accept SS >= +40 / FF >= +15 here).
# The vehicle's IO is false-pathed as in its route (route_ctl3.sh FPIO=1); corner_sta --post-sdc re-times the routed block.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_propagated_clock [all_clocks]
set_false_path -from [all_inputs -no_clocks]
set_false_path -to [all_outputs]
