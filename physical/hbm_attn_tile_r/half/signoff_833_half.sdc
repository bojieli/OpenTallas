# el1011-hbm-attn (textbook audit class 1, 2026-10-11): the attention HALF's clock port is ck (hfd_attn_half_lo/hi 'input [0:0] ck').
# signoff_833_int.sdc / run_abi3_physical's default --clock-port clk left core_clk VIRTUAL on every half route: CTS found 0 clock
# nets, no clock tree over the 1,778-um half, no reg-to-reg path timed (report_clock_skew: no launch/capture paths).
# H16 quad parent internal sign-off at 833.333 ps (route at 770): re-clocks the routed tile; IO is signed off by
# measure_io_latency.tcl against the measured latencies.
create_clock -name core_clk -period 833.333 [get_ports ck]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
