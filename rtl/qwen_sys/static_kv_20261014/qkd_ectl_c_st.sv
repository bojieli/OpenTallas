`timescale 1ns/1ps
`ifndef KVD_ECSTMUT
`define KVD_ECSTMUT 0
`endif
// RTL-BUILD-KV/ASTK 2026-10-18: the static ECTL C leaf qkd_ectl_c_st (see qkd_static_ectl_st.sv for the frame and the proof).
module qkd_ectl_c_st #(parameter integer QK_ISSUE_AGE=34, parameter integer ROW_RETURN_LAT=9, parameter integer HXK=0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    cfg,
    input  wire [632:0]  si,             // E: {er_data 64, exp_done 32, q_data 512, q_beat 6, q_valid, cyc8 3, T 14, start}
    output wire [412:0]  so,             // E: {fault, lmax_any 2, lmax 256, sc_data 128, sc_addr 12, sc_valid, er_addr 12, er_valid}
    output wire [15:0]   e0, e1, e2, e3,
    input  wire [33:0]   s0, s1, s2, s3,
    output wire [518:0]  t0_q,
    output wire [518:0]  t1_q,
    input  wire          rsv_i,
    output wire [51:0]   x_b,
    output wire [51:0]   x_a
);
    wire k_done, fault;
    wire [511:0] q_d = (`KVD_ECSTMUT == 2) ? {si[535:25], 1'b0} : si[536:25];
    ot_qkd_ectl_part #(.STATIC_QK(1), .QK_ISSUE_AGE(QK_ISSUE_AGE), .ROW_RETURN_LAT(ROW_RETURN_LAT), .HXK(HXK), .PART(3), .HEADS(1), .Q_FP32(1)) u (.clk(ck), .rst_n(rst_n), .cfg_s(cfg[1:0]), .cfg_e(cfg[4:2]),
        .start_in(si[0]), .T_in(si[14:1]), .cyc8_in(si[17:15]), .q_valid_in(si[18]), .q_beat_in(si[24:19]),
        .q_data_in(q_d), .exp_done(si[568:537]), .er_data(si[632:569]), .nb_cr(1'b0),
        .er_valid(so[0]), .er_addr(so[12:1]), .sc_valid(so[13]), .sc_addr(so[25:14]), .sc_data(so[153:26]),
        .lmax(so[409:154]), .lmax_any(so[411:410]), .nb_valid(), .nb_beat(), .nb_g(),
        .nb_gam(), .k_done(k_done), .v_done(), .fault(fault), .ev_k_first(), .ev_v_first(),
        .req_valid(), .req_v(), .req_g(), .req_t(), .rsp_valid_in(1'b0), .rsp_data_in(1024'd0),
        .x_i(52'd0), .x_o(), .x2_o(x_a), .rsv_i(rsv_i), .rsv_o(), .rvm_i(1'b0), .rvm_o(), .rsd_i(512'd0), .rsd_o(),
        .t0_c(), .t1_c(), .t0_row(), .t1_row(), .t0_e({e1, e0}), .t1_e({e3, e2}), .t0_lt(), .t1_lt(),
        .t0_qv(t0_q[0]), .t1_qv(t1_q[0]), .t0_qb(t0_q[6:1]), .t1_qb(t1_q[6:1]), .t0_qd(t0_q[518:7]), .t1_qd(t1_q[518:7]),
        .ts0_sc({s1[31:0], s0[31:0]}), .ts0_sf({s1[32], s0[32]}), .ts0_gf({s1[33], s0[33]}),
        .ts1_sc({s3[31:0], s2[31:0]}), .ts1_sf({s3[32], s2[32]}), .ts1_gf({s3[33], s2[33]}));
    assign so[412] = (`KVD_ECSTMUT == 1) ? k_done : fault;
    assign x_b = x_a;
endmodule
