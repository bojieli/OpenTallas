# hfd_svc_SW_s0: forwarded input clocks (two-clock FIFO writes, asynchronous to ck)
create_clock -name fq0 -period 0.833 [get_ports {q0[44]}]
set_clock_uncertainty -setup 0.060 [get_clocks {fq0}]
set_clock_uncertainty -hold 0.025 [get_clocks {fq0}]
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks fq0]
