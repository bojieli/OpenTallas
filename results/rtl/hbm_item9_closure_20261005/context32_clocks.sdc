# ASAP7 ps units. Actual unchanged reset-controller clocks; no clock/reset waivers.
create_clock -name mem_clk -period 833 -waveform {0 416.5} [get_ports clk_mem]
create_clock -name host_clk -period 833 -waveform {0 416.5} [get_ports clk_host]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# These are synchronous same-frequency source roots. No asynchronous clock groups.
