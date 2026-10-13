read_liberty /work/cf_ss_no_tree.lib
read_liberty /work/sink.lib
read_verilog /work/probe.v
link_design probe
create_clock -period 833.333 [get_ports clk]
set_clock_latency 203.6 [get_pins {cf0/cr[0]}]
set_clock_latency 368.7 [get_pins r/ck]
set_clock_uncertainty -hold 50 [all_clocks]
set_clock_uncertainty -setup 85 [all_clocks]
report_checks -path_delay max -group_path_count 4 -endpoint_path_count 1 -digits 3
report_worst_slack -max -digits 3
