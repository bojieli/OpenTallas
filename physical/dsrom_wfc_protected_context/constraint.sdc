# ASAP7 liberty units are ps. Common PLL, related phase-zero 3:4 roots.
create_clock -name clk_fast -period 833.333333333 [get_ports fast_clk]
create_generated_clock -name clk_serial -source [get_ports fast_clk] -multiply_by 3 -divide_by 4 [get_ports slow_clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# External engine/link/host/XB arrival and receiver loads remain owner-unbound.
# No default IO fraction, load, asynchronous clock exception or false path.
# Internal connected controller/producer/provider/C8 timing only until receipt.
