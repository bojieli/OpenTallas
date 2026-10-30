# source-synchronous ring inputs (COORD 10-29 21:11): timed against their forwarded write clock, not vclk (landing_contract.ring_input_sdc)
# OT_FWD_RING_INPUTS fclk_in_d_i d_i[*] cland_dn_ready_d_i cland_dn_fault_d_i
set_input_delay -max 699.7200 -clock fclk_in_d_i [get_ports {d_i[*]}]
set_input_delay -min -40.0000 -clock fclk_in_d_i [get_ports {d_i[*]}]
set_input_delay -max 166.6000 -clock fclk_in_d_i [get_ports {cland_dn_ready_d_i}]
set_input_delay -min -40.0000 -clock fclk_in_d_i [get_ports {cland_dn_ready_d_i}]
set_input_delay -max 166.6000 -clock fclk_in_d_i [get_ports {cland_dn_fault_d_i}]
set_input_delay -min -40.0000 -clock fclk_in_d_i [get_ports {cland_dn_fault_d_i}]
# OT_FWD_RING_INPUTS fclk_in_u_i u_i[*] cland_dn_ready_u_i cland_dn_fault_u_i
set_input_delay -max 699.7200 -clock fclk_in_u_i [get_ports {u_i[*]}]
set_input_delay -min -40.0000 -clock fclk_in_u_i [get_ports {u_i[*]}]
set_input_delay -max 166.6000 -clock fclk_in_u_i [get_ports {cland_dn_ready_u_i}]
set_input_delay -min -40.0000 -clock fclk_in_u_i [get_ports {cland_dn_ready_u_i}]
set_input_delay -max 166.6000 -clock fclk_in_u_i [get_ports {cland_dn_fault_u_i}]
set_input_delay -min -40.0000 -clock fclk_in_u_i [get_ports {cland_dn_fault_u_i}]
