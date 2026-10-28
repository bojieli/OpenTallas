# Clear only the pre-CTS LOCAL network estimate; preserve early core source latencies.
unset_clock_latency -clock clk [get_ports {clk}]
source /work/clock_taps.tcl

set rt_postplace 1
set rt_leaf_reach_um 800 ;# DRT-TRIAL-1 trial-local: plan reset in_site (531.9,4.3) is 646 um from the W face regs (gate 405 FAIL, reported)
source /work/reset_taps.tcl
unset rt_postplace
