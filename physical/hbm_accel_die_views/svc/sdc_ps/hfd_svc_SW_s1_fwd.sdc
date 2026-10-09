# hfd_svc_SW_s1: forwarded input clocks (two-clock FIFO writes, asynchronous to ck); forwarded-clock output bits
create_clock -name fq2 -period 833 [get_ports {q2[44]}]
for {set i 0} {$i < 44} {incr i} { set_input_delay -clock fq2 166.6 [get_ports [format {q2[%d]} $i]] }
create_clock -name fkq2 -period 833 [get_ports {kq2[3]}]
for {set i 0} {$i < 3} {incr i} { set_input_delay -clock fkq2 166.6 [get_ports [format {kq2[%d]} $i]] }
set_false_path -to [get_ports -quiet {kv[1038] kv[1039] kv[1040] l2[1099] l2[1100] l2[1101] ik[1024] ik[1025] ks2[1099] ks2[1100] ks2[1101]}]
set_clock_uncertainty -setup 60 [get_clocks {fq2 fkq2}]
set_clock_uncertainty -hold 25 [get_clocks {fq2 fkq2}]
set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] -group [get_clocks fq2] -group [get_clocks fkq2]
