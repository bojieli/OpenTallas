# H16 quad parent internal sign-off at 833.333 ps (route at 770): re-clocks the routed tile; IO is signed off by
# measure_io_latency.tcl against the measured latencies.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
