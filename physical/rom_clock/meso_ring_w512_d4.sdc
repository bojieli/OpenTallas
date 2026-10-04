# ot_meso_fifo (free-running ring, reset-placed pointer, opposite-edge phase guards), W=512 DEPTH=4 OFFSET=1.
# Two clocks of equal period and unknown static phase.  No clock groups and no false paths.
create_clock -name wclk -period 833.333 [get_ports wclk]
create_clock -name rclk -period 833.333 [get_ports rclk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# Phase-window budget of every cross-clock arc (ring slot data/valid/lap -> read mux -> receive buffer, outputs,
# guard and Gray-sample flops): the low guard trips at lag < (GUARD_LO + 0.5) T = 416.667 ps, so every arc must
# settle within T/2 - 60 ps.  Hold: the slot is rewritten DEPTH periods after its write, the high guard trips at a
# lag of 2.5 T, so the arcs need only a non-negative datapath delay.
set_max_delay -ignore_clock_latency 356.667 -from [get_clocks wclk] -to [get_clocks rclk]
set_max_delay -ignore_clock_latency 356.667 -from [get_clocks rclk] -to [get_clocks wclk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks wclk] -to [get_clocks rclk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks rclk] -to [get_clocks wclk]
set_input_delay 166.666 -clock wclk [get_ports {wrst_n w_v w_d*}]
set_input_delay 166.666 -clock rclk [get_ports {rrst_n r_rdy}]
set_output_delay 166.666 -clock wclk [get_ports {w_rdy w_live w_fault}]
set_output_delay 166.666 -clock rclk [get_ports {r_live r_fault}]
# r_v / r_d feed the consumer's input register directly (fall-through): its setup plus local wire, 0.1 T.
set_output_delay 83.333 -clock rclk [get_ports {r_v r_d*}]
set_max_fanout 32 [current_design]
