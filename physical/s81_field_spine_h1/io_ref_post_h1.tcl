# s81-fieldphase 2026-10-07 RULE H1 (flow-hold): a die link's hold budget is carried ONCE, by the sender's output min
# delay; this block's input min is its own boundary-register arrival (0), output min stays -50.  Otherwise identical to
# physical/s81_pq_r128_expanded/io_ref_post.tcl (v13b d0178820d).
# DS-ROM field spine v13b ORFS step hook (POST_CTS, POST_GLOBAL_ROUTE): put the PLAIN IO budget form back
# (io_budget_r<R>.sdc) before the stage writes its SDC, so the next stage never loads -reference_pin delays
# (see io_ref_pre.tcl).
set fs_in [get_ports {go i_ph* i_np* i_xbase* i_xps* i_obase* i_ops* i_fmt* x_q* r_v* r_row* r_pos* r_fp32* r_bf16* r_e* f_fault}]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay  250 -max -clock core_clk $fs_in
set_input_delay    0 -min -clock core_clk $fs_in
set_output_delay 250 -max -clock core_clk [all_outputs]
set_output_delay -50 -min -clock core_clk [all_outputs]
set_false_path -from [get_ports {rw_ph rw_st rw_a* rw_d* rst_n}]
puts "OT_FS_IO plain budget restored"
