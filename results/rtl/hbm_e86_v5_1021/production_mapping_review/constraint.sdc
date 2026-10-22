# Synthesis-only planning clock ABI; no timing result qualifies this experiment.
set clk_period 833.333333
foreach p {clk clk_r0 clk_r1 clk_r2 clk_r3} {
  create_clock -name $p -period $clk_period [get_ports $p]
}
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
