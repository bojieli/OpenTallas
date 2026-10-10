# Candidate external clock input contract. External generation is assumed, not measured.
# Serial and stream retain the specified 3:4 rational relationship.
create_clock -name clk_stream -period 0.833333333 [get_ports clk_stream]
create_generated_clock -name clk_serial -source [get_ports clk_stream] -multiply_by 3 -divide_by 4 [get_ports clk_serial]
create_clock -name clk_hbm -period 1.024 [get_ports clk_hbm]
create_clock -name clk_link -period 0.833333333 [get_ports clk_link]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# No asynchronous clock groups or reset false paths: crossings remain visible until proved.
