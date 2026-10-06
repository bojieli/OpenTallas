# su_softmax round 5 sign-off clock (owner margin-first rule 2026-10-06): the block is routed against an
# over-constrained 0.770 ns clock and signed off at 0.833333 ns, SS setup 60 ps / FF hold 25 ps uncertainty.
# Read by tools/w18/corner_sta.py --post-sdc after the routed design's own SDC (time unit ps).
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
