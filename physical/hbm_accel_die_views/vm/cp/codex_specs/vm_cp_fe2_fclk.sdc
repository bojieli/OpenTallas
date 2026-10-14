# vm_cp_fe2: xNE[2063] xNE[2064] xNE[2065] xNE[2066] xNE[2067] are FORWARDED clocks (ot_fwd_clk_inv of ck, kept inverter at the face), not data
# outputs: the all_outputs data budget (0.2 T referenced to the tree insertion) timed ck -> fclk as data (g1/g2 gates:
# the only negative class; fe2 CTS setup repair from -327 ps crashed ODB-0445). Same modelling as the closed
# hattn_ks_entry (ks_entry_fwd.sdc). Period, uncertainty and every data boundary are unchanged. OPEN at die level:
# fclk-to-data offset = this tile's routed clock insertion; the receiver's source-synchronous budget must use it.
set_false_path -to [get_ports {xNE[2063]}]
set_false_path -to [get_ports {xNE[2064]}]
set_false_path -to [get_ports {xNE[2065]}]
set_false_path -to [get_ports {xNE[2066]}]
set_false_path -to [get_ports {xNE[2067]}]
