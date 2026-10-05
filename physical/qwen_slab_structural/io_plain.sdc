# Boundary delays, clock-port referenced (the form every ORFS stage loads and writes back).
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay 166.667 -clock clk [get_ports {rst_n p_* res_in*}]
set_output_delay 166.667 -clock clk [get_ports {o_we o_addr* o_mask* o_data* ov am_tv am_top* am_rmax fault}]
