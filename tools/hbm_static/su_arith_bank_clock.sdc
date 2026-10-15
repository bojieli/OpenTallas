create_clock -name core_clk -period 1111.111111 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
