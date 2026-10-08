# Headline clock and unchanged 60/25 ps sign-off policy. Route still targets 770 ps.
# Re-propagate after replacing the route clock, before io_ref_skew measures insertion.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_propagated_clock [all_clocks]
