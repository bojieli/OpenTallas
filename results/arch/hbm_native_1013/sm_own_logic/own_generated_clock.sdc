# This port is the retained ICG GCLK output, not a data signal.
# Model its actual source latency; all 617 data/control cut nets retain normal IO constraints.
unset_output_delay [get_ports cut_7768]
create_generated_clock -name own_gated_fwd -source [get_ports cut_2] -master_clock core_clk -divide_by 1 [get_ports cut_7768]
set_propagated_clock [get_clocks own_gated_fwd]
set_clock_uncertainty -setup 60 [get_clocks own_gated_fwd]
set_clock_uncertainty -hold 25 [get_clocks own_gated_fwd]
