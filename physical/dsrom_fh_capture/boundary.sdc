# Only stand-in ports at already represented parent registers are excluded.
# Every internal SRAM read/capture, address, protection, and clock path remains.
set_false_path -from [get_ports {s3_v_in a_tag_p_in[*] res_in[*] go_fus i_iaddr[*] busy_in[*] o_we1_in[*] o_addr1_in[*] o_mask1_in[*] leaf_mask_in[*] leaf_row_in[*] tv_in ov1_in am_idx_in[*] wr_en[*] wr_addr[*] wr_mask[*] wr_data[*] rst_n}]
# Actual consumer data/valid/row/address registers represent the next parent
# stage; output stand-ins are not a parent or full-target timing proof.
set_false_path -to [all_outputs]
