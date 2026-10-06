# su_softmax round 5 sign-off clock (owner margin-first rule 2026-10-06): the block is routed against an
# over-constrained 0.770 ns clock and signed off at 0.833333 ns, SS setup 60 ps / FF hold 25 ps uncertainty.
# Read by tools/w18/corner_sta.py --post-sdc after the routed design's own SDC (time unit ps).
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
# m5c onward: the route's IO virtual clock follows the sign-off period (its latency and IO delays are those of
# boundary_io_vclk.sdc); the IO is also re-timed against the measured per-corner insertion by io_budget.sh.
if {[llength [get_clocks -quiet vclk]]} {
  create_clock -name vclk -period 833.333
  set_clock_uncertainty -setup 60 [get_clocks vclk]
  set_clock_uncertainty -hold 25 [get_clocks vclk]
  set_clock_latency 834 [get_clocks vclk]
}
