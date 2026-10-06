# hfd_index_q: forwarded index-key clocks (k[1024], k[1025]) at the stream clock period; they only write two-clock
# FIFOs (ot_hbm_accel_cdc_fifo, falling-edge capture via ~k[1024+g]), asynchronous to ck
create_clock -name fk0 -period 0.833 [get_ports {k[1024]}]
create_clock -name fk1 -period 0.833 [get_ports {k[1025]}]
set_clock_uncertainty -setup 0.060 [get_clocks {fk0 fk1}]
set_clock_uncertainty -hold 0.025 [get_clocks {fk0 fk1}]
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks fk0] -group [get_clocks fk1]
