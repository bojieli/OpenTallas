# hfd_svc_SW: forwarded input clocks (row-1 SM requests, e) at the stream clock period; they only write
# two-clock FIFOs (ot_hbm_accel_cdc_fifo), asynchronous to ck (clk_hbm)
create_clock -name fq0 -period 0.833 [get_ports {qsm4[44]}]
create_clock -name fq2 -period 0.833 [get_ports {qsm5[44]}]
create_clock -name fq4 -period 0.833 [get_ports {qsm6[44]}]
create_clock -name fq6 -period 0.833 [get_ports {qsm7[44]}]
create_clock -name fe -period 0.833 [get_ports {e[128]}]
set_clock_uncertainty -setup 0.060 [get_clocks {fq0 fq2 fq4 fq6 fe}]
set_clock_uncertainty -hold 0.025 [get_clocks {fq0 fq2 fq4 fq6 fe}]
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks fq0] -group [get_clocks fq2] -group [get_clocks fq4] -group [get_clocks fq6] -group [get_clocks fe]
