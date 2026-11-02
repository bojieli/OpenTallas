// Requires the matching four carrier projections; NOT APPLIED.
ot_hbm_obs_leaf_fc136 #(.LID(0), .SYNC_MASK(512'd0)) u_u_obs_C (
        .clk(clk),
        .obs({w_u_vm_status4_vmstat[18:0], w_u_tkm_SW_stat_cycles[31:0], w_u_host_status_a_cause[1:0], L48_i_q[17:7], w_u_hc_eng_program_done[0], w_u_hb_idx_link_selected_count[9:0], w_u_hb_idx_ctl_topk_done[0], w_u_hb_argmax_done[0], w_u_hb_argmax_cq_seq[1:0], L138m_i_q[1:0], L117m_i_q[8:0], L201_i_q[1:0], L141_i_q[0], L118_i_q[8:1], L138_i_q[1:0], L117_i_q[8:0], L48m_i_q[5:0], L125m_i_q[4:0], L48_i_q[5:0], L125_i_q[6:0]}),
        .q_d(w_u_host_cp_ingress_obs_q_d[31:0]),
        .q_idx(w_u_host_cp_ingress_obs_q_idx[7:0]),
        .q_v(w_u_host_cp_ingress_obs_q_v[0]),
        .r_d(w_u_obs_C_r_d),
        .r_idx(w_u_obs_C_r_idx),
        .r_v(w_u_obs_C_r_v),
        .rst_n(rst_n)
    );
