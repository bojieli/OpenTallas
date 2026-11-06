module native_brmw_ne;
    wire [25:0] w_u_xl_Q_ctl_q1_bsel;
    ot_hgi_sm_xload_cl2_bdring #(.NR(32), .PMAX(8)) u_u_xq_Q_p0_bd (
        .bq_d(w_u_xq_Q_p0_bd_bq_d),
        .bsel(w_u_xl_Q_ctl_q1_bsel[25:0]),
        .clk(clk),
        .lane_en_i(w_u_xl_Q_ctl_q1_lane_en[63:0]),
        .qe_hi(w_u_xl_Q_aqhi_e[9:0]),
        .qe_lo(w_u_xl_Q_aqlo_e[9:0]),
        .qq_hi(w_u_xl_Q_aqhi_q[255:0]),
        .qq_lo(w_u_xl_Q_aqlo_q[255:0]),
        .r_wsel(w_u_xl_Q_ctl_q1_r_wsel[15:0]),
        .zhi(w_u_xl_Q_ctl_q1_zhi[0]),
        .zlo(w_u_xl_Q_ctl_q1_zlo[0])
    );
    ot_hgi_sm_xload_cl2_bdring #(.NR(32), .PMAX(8)) u_u_xq_Q_p1_bd (
        .bq_d(w_u_xq_Q_p1_bd_bq_d),
        .bsel(w_u_xl_Q_ctl_q1_bsel[25:0]),
        .clk(clk),
        .lane_en_i(w_u_xl_Q_ctl_q1_lane_en[63:0]),
        .qe_hi(w_u_xl_Q_aqhi_e[9:0]),
        .qe_lo(w_u_xl_Q_aqlo_e[9:0]),
        .qq_hi(w_u_xl_Q_aqhi_q[255:0]),
        .qq_lo(w_u_xl_Q_aqlo_q[255:0]),
        .r_wsel(w_u_xl_Q_ctl_q1_r_wsel[15:0]),
        .zhi(w_u_xl_Q_ctl_q1_zhi[0]),
        .zlo(w_u_xl_Q_ctl_q1_zlo[0])
    );
endmodule
