# SS technology mapping target only. No physical or loaded-I/O closure claim.
create_clock -name clk -period 833.3333333333334 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
