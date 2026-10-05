set clk_period 833
create_clock -name core_clk -period $clk_period [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_max_fanout 32 [current_design]
set_max_transition 250 [current_design]
set_false_path -from [get_ports {s3_v_in a_tag_p_in[*] res_in[*] go_fus i_iaddr[*] busy_in[*] o_we1_in[*] o_addr1_in[*] o_mask1_in[*] leaf_mask_in[*] leaf_row_in[*] tv_in ov1_in am_idx_in[*] rst_n}]
set_false_path -to [remove_from_collection [all_outputs] [get_ports {ra_re[*] ra_addr[*]}]]
# SRAM input hold is checked in this child measurement.
