# hfd_svc_SW_s3: forwarded input clocks (two-clock FIFO writes, asynchronous to ck)
create_clock -name fq4 -period 833 [get_ports {q4[44]}]
for {set i 0} {$i < 44} {incr i} { set_input_delay -clock fq4 166.6 [get_ports [format {q4[%d]} $i]] }
create_clock -name fe -period 833 [get_ports {e[128]}]
for {set i 0} {$i < 128} {incr i} { set_input_delay -clock fe 166.6 [get_ports [format {e[%d]} $i]] }
set_clock_uncertainty -setup 60 [get_clocks {fq4 fe}]
set_clock_uncertainty -hold 25 [get_clocks {fq4 fe}]
set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] -group [get_clocks fq4] -group [get_clocks fe]
