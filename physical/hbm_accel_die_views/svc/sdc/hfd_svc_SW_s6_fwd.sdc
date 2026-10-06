# hfd_svc_SW_s6: forwarded input clocks (two-clock FIFO writes, asynchronous to ck)
create_clock -name fq6 -period 0.833 [get_ports {q6[44]}]
set_clock_uncertainty -setup 0.060 [get_clocks {fq6}]
set_clock_uncertainty -hold 0.025 [get_clocks {fq6}]
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks fq6]
