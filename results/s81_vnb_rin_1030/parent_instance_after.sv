    // PRIVATE registered-input cut: same actual 32 flops, same edge/reset.
    wire vnb_chain_rs_c;
    reg vnb_chain_v_q; reg [30:0] vnb_chain_s_q;
    always @(posedge clk or negedge vnb_chain_rs_c)
        if (!vnb_chain_rs_c) vnb_chain_v_q <= 1'b0;
        else vnb_chain_v_q <= w_u_vn_u_a_c_v[0];
    always @(posedge clk) vnb_chain_s_q <= w_u_vn_u_a_c_s[30:0];
    ot_s81sl_vn_b_rin #(.HW_STAGE(0), .LA(6), .LM(5)) u_u_vn_u_b (
        .c_s_q(vnb_chain_s_q),
        .c_v_q(vnb_chain_v_q),
        .chain_rs_c(vnb_chain_rs_c),
        .clk(clk),
        .fault(w_u_vn_u_b_fault),
        .hq_d(w_u_vn_u_b_hq_d),
        .hq_v(w_u_vn_u_b_hq_v),
        .hr_hf(w_u_cst_vni_0_Y[387]),
        .hr_j(w_u_cst_vni_0_Y[390:388]),
        .hr_v(w_u_cst_vni_1_Y[2]),
        .hw_d(w_u_cst_vni_0_Y[646:391]),
        .hw_hf(w_u_cst_vni_0_Y[647]),
        .hw_j(w_u_cst_vni_0_Y[650:648]),
        .hw_v(w_u_cst_vni_1_Y[3]),
        .n_go(w_u_cst_vni_1_Y[1]),
        .n_pre(w_u_cst_vni_0_Y[386:259]),
        .p_d(w_u_vn_u_b_p_d),
        .p_v(w_u_vn_u_b_p_v),
        .rb_d(leafdn_i0_q[31:0]),
        .rb_v(leafdn_i0_q[32]),
        .rst_n(rst_n),
        .wl_d(w_u_cst_vni_0_Y[255:128]),
        .wl_i(w_u_cst_vni_0_Y[258:256]),
        .wl_v(w_u_cst_vni_1_Y[0]),
        .y(w_u_vn_u_b_y),
        .y_i(w_u_vn_u_b_y_i),
        .y_v(w_u_vn_u_b_y_v)
    );
