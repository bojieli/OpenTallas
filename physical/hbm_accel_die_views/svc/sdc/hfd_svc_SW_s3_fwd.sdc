# hfd_svc_SW_s3: forwarded input clocks (two-clock FIFO writes, asynchronous to ck)
create_clock -name fq4 -period 0.833 [get_ports {q4[44]}]
create_clock -name fe -period 0.833 [get_ports {e[128]}]
set_clock_uncertainty -setup 0.060 [get_clocks {fq4 fe}]
set_clock_uncertainty -hold 0.025 [get_clocks {fq4 fe}]
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks fq4] -group [get_clocks fe]
