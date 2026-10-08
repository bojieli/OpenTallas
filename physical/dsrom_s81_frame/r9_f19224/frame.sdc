# GENERATED (CLAUDE S81-RERUN): S81 frame block -- the column FIFO's forwarded write clock (x stream from the
# trunk tap station) and the meso phase-window budget of physical/rom_clock/meso_ring_w512_d4.sdc
create_clock -name xf -period 833.333 [get_ports {xf}]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set _ck [get_clocks -quiet {core_clk clk ck}]
set_max_delay -ignore_clock_latency 356.667 -from [get_clocks xf] -to $_ck
set_max_delay -ignore_clock_latency 356.667 -from $_ck -to [get_clocks xf]
set_min_delay -ignore_clock_latency 0 -from [get_clocks xf] -to $_ck
set_min_delay -ignore_clock_latency 0 -from $_ck -to [get_clocks xf]
set_input_delay 166.666 -clock xf [get_ports {xd[*]}]
# rf: forwarded return clock (= the column clock) leaves with its data
