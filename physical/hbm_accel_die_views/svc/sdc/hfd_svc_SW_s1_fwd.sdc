# hfd_svc_SW_s1: forwarded input clocks (two-clock FIFO writes, asynchronous to ck)
create_clock -name fq2 -period 833 [get_ports {q2[44]}]
for {set i 0} {$i < 44} {incr i} { set_input_delay -clock fq2 166.6 [get_ports [format {q2[%d]} $i]] }
set_clock_uncertainty -setup 60 [get_clocks {fq2}]
set_clock_uncertainty -hold 25 [get_clocks {fq2}]
set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] -group [get_clocks fq2]
