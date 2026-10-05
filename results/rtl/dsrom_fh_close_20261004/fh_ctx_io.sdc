# ot_hdc_v41_fh_ctx boundary: every port except ra_q stands in for a register INSIDE ot_hdc_v41_matvec (the
# context's first / last flops are those registers), so port-to-flop and flop-to-port paths are zero-logic
# stand-ins whose only "delay" is the context's own clock-tree latency against an ideal-clock port: excluded.
# ra_q is the vector memory's read data, which feeds the fused adder's first stage: setup keeps the 0.2-period
# input budget (the SRAM's clock-to-q); its hold is against the same clock tree as the SRAM, excluded here.
set_false_path -from [get_ports {s3_v_in a_tag_p_in[*] res_in[*] go_fus i_iaddr[*] busy_in[*] o_we1_in[*] o_addr1_in[*] o_mask1_in[*] leaf_mask_in[*] leaf_row_in[*] tv_in ov1_in am_idx_in[*] rst_n}]
set_false_path -to [all_outputs]
set_false_path -hold -from [get_ports {ra_q[*]}]
