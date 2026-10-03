# Independent phase. Both local periods constrained; no phase alignment claim.
create_clock -name write -period 833.333 [get_ports wclk]
create_clock -name read -period 833.333 [get_ports rclk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# Every cross-clock arc is bounded, including all payload/mux arcs.
# The 773.333ps upper bound also bounds Gray-bit skew below one source period.
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks write] -to [get_clocks read]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks read] -to [get_clocks write]
set_min_delay -ignore_clock_latency 0 -from [get_clocks write] -to [get_clocks read]
set_min_delay -ignore_clock_latency 0 -from [get_clocks read] -to [get_clocks write]
set_input_delay 166.666 -clock write [get_ports {wrst_n w_v w_d*}]
set_input_delay 166.666 -clock read [get_ports {rrst_n r_rdy}]
set_output_delay 166.666 -clock write [get_ports {w_rdy w_live w_fault}]
set_output_delay 166.666 -clock read [get_ports {r_v r_d* r_live r_fault}]
set_max_fanout 32 [current_design]
