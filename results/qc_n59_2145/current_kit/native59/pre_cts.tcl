# Clear only the pre-CTS LOCAL network estimate; preserve early core source latencies.
unset_clock_latency -clock clk [get_ports {clk clk_t1 clk_t2 clk_t3}]
source /work/clock_taps.tcl

set rt_postplace 1
set rt_leaf_reach_um 405
source /work/reset_taps.tcl
unset rt_postplace
