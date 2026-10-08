# Source-owned real P2 stack clocks, ASAP7 library ps. No clock/IO waiver.
# stream_clk source is core_clk at exactly833.333333333ps from the driver.
create_clock -name h_clk -period 1024 [get_ports service_clk]
set_clock_uncertainty -setup 60 [get_clocks h_clk]
set_clock_uncertainty -hold 25 [get_clocks h_clk]
# Coded dual-clock FIFOs and explicit dual-rail synchronizers are the actual
# asynchronous paths. Macro/correction/SM captures retain their real clocks.
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks h_clk]
remove_input_delay [all_inputs -no_clocks]
remove_output_delay [all_outputs]
# Appended parent SDC must contain actual outer PHY/router/SM source timings
# and loads. No generic20% boundary is a parent qualification proof.
