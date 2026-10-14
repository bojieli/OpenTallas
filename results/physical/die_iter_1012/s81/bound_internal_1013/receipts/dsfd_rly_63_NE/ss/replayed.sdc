###############################################################################
# Created by write_sdc
###############################################################################
current_design dsfd_rly_63_NE
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clk -period 833.3330 [get_ports {ck}]
set_clock_uncertainty -setup 60.0000 core_clk
set_clock_uncertainty -hold 25.0000 core_clk
set_propagated_clock [get_clocks {core_clk}]
create_clock -name ot_lb_v_core_clk -period 770.0000 
set_clock_uncertainty -setup 60.0000 ot_lb_v_core_clk
set_clock_uncertainty -hold 25.0000 ot_lb_v_core_clk
set_clock_latency 90.4358 [get_clocks {ot_lb_v_core_clk}]
set_clock_latency -source 0.0000 [get_clocks {ot_lb_v_core_clk}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[0]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[0]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[10]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[10]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[11]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[11]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[12]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[12]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[13]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[13]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[14]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[14]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[15]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[15]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[16]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[16]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[17]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[17]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[18]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[18]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[19]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[19]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[1]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[1]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[20]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[20]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[21]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[21]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[22]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[22]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[23]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[23]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[24]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[24]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[25]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[25]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[26]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[26]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[27]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[27]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[28]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[28]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[29]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[29]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[2]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[2]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[30]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[30]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[31]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[31]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[32]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[32]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[33]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[33]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[34]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[34]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[35]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[35]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[36]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[36]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[37]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[37]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[38]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[38]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[39]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[39]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[3]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[3]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[40]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[40]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[41]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[41]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[42]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[42]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[43]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[43]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[44]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[44]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[45]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[45]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[46]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[46]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[47]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[47]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[48]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[48]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[49]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[49]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[4]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[4]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[50]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[50]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[51]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[51]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[52]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[52]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[53]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[53]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[54]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[54]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[55]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[55]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[56]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[56]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[57]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[57]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[58]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[58]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[59]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[59]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[5]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[5]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[60]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[60]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[61]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[61]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[62]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[62]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[6]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[6]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[7]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[7]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[8]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[8]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[9]}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[9]}]
set_input_delay 81.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {rs}]
set_input_delay 348.1167 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {rs}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[0]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[0]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[10]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[10]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[11]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[11]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[12]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[12]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[13]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[13]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[14]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[14]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[15]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[15]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[16]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[16]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[17]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[17]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[18]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[18]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[19]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[19]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[1]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[1]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[20]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[20]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[21]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[21]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[22]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[22]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[23]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[23]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[24]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[24]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[25]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[25]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[26]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[26]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[27]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[27]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[28]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[28]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[29]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[29]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[2]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[2]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[30]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[30]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[31]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[31]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[32]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[32]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[33]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[33]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[34]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[34]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[35]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[35]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[36]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[36]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[37]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[37]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[38]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[38]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[39]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[39]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[3]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[3]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[40]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[40]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[41]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[41]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[42]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[42]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[43]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[43]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[44]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[44]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[45]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[45]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[46]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[46]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[47]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[47]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[48]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[48]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[49]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[49]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[4]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[4]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[50]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[50]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[51]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[51]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[52]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[52]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[53]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[53]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[54]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[54]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[55]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[55]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[56]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[56]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[57]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[57]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[58]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[58]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[59]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[59]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[5]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[5]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[60]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[60]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[61]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[61]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[62]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[62]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[6]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[6]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[7]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[7]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[8]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[8]}]
set_output_delay -131.0728 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[9]}]
set_output_delay 165.2173 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[9]}]
set_false_path\
    -from [get_clocks {ot_lb_v_core_clk}]\
    -to [list [get_pins {u.o[0]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[0]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[10]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[10]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[11]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[11]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[12]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[12]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[13]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[13]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[14]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[14]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[15]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[15]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[16]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[16]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[17]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[17]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[18]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[18]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[19]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[19]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[1]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[1]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[20]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[20]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[21]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[21]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[22]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[22]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[23]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[23]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[24]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[24]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[25]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[25]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[26]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[26]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[27]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[27]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[28]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[28]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[29]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[29]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[2]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[2]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[30]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[30]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[31]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[31]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[32]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[32]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[33]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[33]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[34]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[34]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[35]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[35]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[36]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[36]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[37]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[37]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[38]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[38]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[39]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[39]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[3]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[3]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[40]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[40]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[41]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[41]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[42]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[42]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[43]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[43]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[44]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[44]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[45]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[45]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[46]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[46]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[47]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[47]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[48]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[48]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[49]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[49]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[4]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[4]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[50]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[50]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[51]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[51]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[52]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[52]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[53]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[53]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[54]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[54]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[55]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[55]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[56]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[56]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[57]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[57]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[58]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[58]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[59]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[59]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[5]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[5]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[60]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[60]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[61]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[61]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[62]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[62]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[6]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[6]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[7]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[7]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[8]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[8]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[9]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[9]$_DFF_PN0_/SETN}]]
###############################################################################
# Environment
###############################################################################
set_input_transition 150.0000 [get_ports {rs}]
set_input_transition 150.0000 [get_ports {i[62]}]
set_input_transition 150.0000 [get_ports {i[61]}]
set_input_transition 150.0000 [get_ports {i[60]}]
set_input_transition 150.0000 [get_ports {i[59]}]
set_input_transition 150.0000 [get_ports {i[58]}]
set_input_transition 150.0000 [get_ports {i[57]}]
set_input_transition 150.0000 [get_ports {i[56]}]
set_input_transition 150.0000 [get_ports {i[55]}]
set_input_transition 150.0000 [get_ports {i[54]}]
set_input_transition 150.0000 [get_ports {i[53]}]
set_input_transition 150.0000 [get_ports {i[52]}]
set_input_transition 150.0000 [get_ports {i[51]}]
set_input_transition 150.0000 [get_ports {i[50]}]
set_input_transition 150.0000 [get_ports {i[49]}]
set_input_transition 150.0000 [get_ports {i[48]}]
set_input_transition 150.0000 [get_ports {i[47]}]
set_input_transition 150.0000 [get_ports {i[46]}]
set_input_transition 150.0000 [get_ports {i[45]}]
set_input_transition 150.0000 [get_ports {i[44]}]
set_input_transition 150.0000 [get_ports {i[43]}]
set_input_transition 150.0000 [get_ports {i[42]}]
set_input_transition 150.0000 [get_ports {i[41]}]
set_input_transition 150.0000 [get_ports {i[40]}]
set_input_transition 150.0000 [get_ports {i[39]}]
set_input_transition 150.0000 [get_ports {i[38]}]
set_input_transition 150.0000 [get_ports {i[37]}]
set_input_transition 150.0000 [get_ports {i[36]}]
set_input_transition 150.0000 [get_ports {i[35]}]
set_input_transition 150.0000 [get_ports {i[34]}]
set_input_transition 150.0000 [get_ports {i[33]}]
set_input_transition 150.0000 [get_ports {i[32]}]
set_input_transition 150.0000 [get_ports {i[31]}]
set_input_transition 150.0000 [get_ports {i[30]}]
set_input_transition 150.0000 [get_ports {i[29]}]
set_input_transition 150.0000 [get_ports {i[28]}]
set_input_transition 150.0000 [get_ports {i[27]}]
set_input_transition 150.0000 [get_ports {i[26]}]
set_input_transition 150.0000 [get_ports {i[25]}]
set_input_transition 150.0000 [get_ports {i[24]}]
set_input_transition 150.0000 [get_ports {i[23]}]
set_input_transition 150.0000 [get_ports {i[22]}]
set_input_transition 150.0000 [get_ports {i[21]}]
set_input_transition 150.0000 [get_ports {i[20]}]
set_input_transition 150.0000 [get_ports {i[19]}]
set_input_transition 150.0000 [get_ports {i[18]}]
set_input_transition 150.0000 [get_ports {i[17]}]
set_input_transition 150.0000 [get_ports {i[16]}]
set_input_transition 150.0000 [get_ports {i[15]}]
set_input_transition 150.0000 [get_ports {i[14]}]
set_input_transition 150.0000 [get_ports {i[13]}]
set_input_transition 150.0000 [get_ports {i[12]}]
set_input_transition 150.0000 [get_ports {i[11]}]
set_input_transition 150.0000 [get_ports {i[10]}]
set_input_transition 150.0000 [get_ports {i[9]}]
set_input_transition 150.0000 [get_ports {i[8]}]
set_input_transition 150.0000 [get_ports {i[7]}]
set_input_transition 150.0000 [get_ports {i[6]}]
set_input_transition 150.0000 [get_ports {i[5]}]
set_input_transition 150.0000 [get_ports {i[4]}]
set_input_transition 150.0000 [get_ports {i[3]}]
set_input_transition 150.0000 [get_ports {i[2]}]
set_input_transition 150.0000 [get_ports {i[1]}]
set_input_transition 150.0000 [get_ports {i[0]}]
###############################################################################
# Design Rules
###############################################################################
set_max_transition 260.0000 [current_design]
set_max_fanout 32.0000 [current_design]
