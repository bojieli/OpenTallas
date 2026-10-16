# H-HARDEN 10-15: hfd_ckgen_rel4 (one leaf, four PLL domains).  core_clk = ck_stream (clock_port); the other three PLL
# outputs enter on their own clock ports, asynchronous to each other.  por_n / locked are asynchronous assert inputs
# (recovery/removal timed per domain flop); rst_* leave from each domain's release flop into the die reset tree.
create_clock -name ck_serial -period 1111.111 [get_ports ck_serial]
create_clock -name ck_hbm -period 1024 [get_ports ck_hbm]
create_clock -name ck_link -period 833.333 [get_ports ck_link]
if {!$::ot_ref_pre_cts} { set_propagated_clock [all_clocks] }
set_clock_uncertainty -setup 60 [get_clocks {ck_serial ck_hbm ck_link}]
set_clock_uncertainty -hold 25 [get_clocks {ck_serial ck_hbm ck_link}]
set_clock_groups -asynchronous -group {core_clk} -group {ck_serial} -group {ck_hbm} -group {ck_link}
