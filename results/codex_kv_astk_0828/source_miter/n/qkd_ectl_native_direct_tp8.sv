`timescale 1ns/1ps
// Direct registered seams (r3): C x2 -> B x1 and C x2 -> A x1 (C x1 is a pure E-pin capture flop); A rv2 -> B rv1 and C rv1.
// Every consumer still sees stage 3. B no longer captures and launches at opposite faces on one flop.
// Fresh native TP8 leaf masters. Historical qkd_ectl_a/b/c views remain on their frozen profile.
// Each native leaf fixes HEADS=1 / Q_FP32=1 independently of global simulation defines.
module qkd_ectl_a_tp8_direct #(parameter integer EPOCH=0, parameter integer STATIC_QK=0, parameter integer QK_ISSUE_AGE=34, parameter integer ROW_RETURN_LAT=9, parameter integer HXK=0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    cfg,            // {e 3, s 2} strap
    output wire [15+EPOCH:0] rq,             // W: {req_t 13, req_g, req_v, req_valid}
    input  wire [1024:0] rs,             // W: {rsp_data 1024, rsp_valid}
    output wire [511:0]  t0_row,         // S / N: row bits [511:0] for the two head-tile pairs
    output wire [511:0]  t1_row,
    input  wire [51:0]   x_i,            // E: stage-2 control word directly from C
    output wire [512:0]  rs_o           // E seam: {row bits [1023:512] 512, rsp_valid}, E-face flops (stage 2), to B and C
);
    wire epoch;
    `ifdef KVD_ECTL_EPOCH_MUT
    if (EPOCH != 0) assign rq[16] = ~epoch;
`else
    if (EPOCH != 0) assign rq[16] = epoch;
`endif
    ot_qkd_ectl_part #(.STATIC_QK(STATIC_QK), .QK_ISSUE_AGE(QK_ISSUE_AGE), .ROW_RETURN_LAT(ROW_RETURN_LAT), .HXK(HXK), .PART(1), .HEADS(1), .Q_FP32(1)) u (.clk(ck), .rst_n(rst_n), .cfg_s(cfg[1:0]), .cfg_e(cfg[4:2]),
        .start_in(1'b0), .T_in(14'd0), .cyc8_in(3'd0), .q_valid_in(1'b0), .q_beat_in(6'd0), .q_data_in(512'd0),
        .exp_done(32'd0), .nb_cr(1'b0), .er_data(64'd0), .er_valid(), .er_addr(), .sc_valid(), .sc_addr(), .sc_data(),
        .lmax(), .lmax_any(), .nb_valid(), .nb_beat(), .nb_g(), .nb_gam(), .k_done(), .v_done(), .fault(), .ev_k_first(),
        .ev_v_first(), .req_epoch(epoch), .req_valid(rq[0]), .req_v(rq[1]), .req_g(rq[2]), .req_t(rq[15:3]), .rsp_valid_in(rs[0]),
        .rsp_data_in(rs[1024:1]), .x_i(x_i), .x_o(), .rsv_i(1'b0), .rsv_o(rs_o[0]), .rvm_i(1'b0), .rvm_o(), .rsd_i(512'd0), .rsd_o(rs_o[512:1]),
        .t0_c(), .t1_c(), .t0_row(t0_row), .t1_row(t1_row), .t0_e(), .t1_e(), .t0_lt(), .t1_lt(), .t0_qv(), .t1_qv(),
        .t0_qb(), .t1_qb(), .t0_qd(), .t1_qd(), .ts0_sc(64'd0), .ts1_sc(64'd0), .ts0_sf(2'd0), .ts1_sf(2'd0),
        .ts0_gf(2'd0), .ts1_gf(2'd0));
endmodule

module qkd_ectl_b_tp8_direct #(parameter integer STATIC_QK=0, parameter integer QK_ISSUE_AGE=34, parameter integer ROW_RETURN_LAT=9, parameter integer HXK=0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    cfg,
    output wire [511:0]  t0_row,         // S / N: row bits [1023:512]
    output wire [511:0]  t1_row,
    output wire [15:0]   t0_cl,          // S / N: {lt 12, c 4}
    output wire [15:0]   t1_cl,
    input  wire [512:0]  rs_i,           // W seam: from A
    input  wire [51:0]   x_i             // E seam: stage-2 control word from C; B's pin flop x1 is stage 3 (XB2, r3)
);
    ot_qkd_ectl_part #(.STATIC_QK(STATIC_QK), .QK_ISSUE_AGE(QK_ISSUE_AGE), .ROW_RETURN_LAT(ROW_RETURN_LAT), .HXK(HXK), .PART(2), .HEADS(1), .Q_FP32(1), .XB2(1)) u (.clk(ck), .rst_n(rst_n), .cfg_s(cfg[1:0]), .cfg_e(cfg[4:2]),
        .start_in(1'b0), .T_in(14'd0), .cyc8_in(3'd0), .q_valid_in(1'b0), .q_beat_in(6'd0), .q_data_in(512'd0),
        .exp_done(32'd0), .nb_cr(1'b0), .er_data(64'd0), .er_valid(), .er_addr(), .sc_valid(), .sc_addr(), .sc_data(),
        .lmax(), .lmax_any(), .nb_valid(), .nb_beat(), .nb_g(), .nb_gam(), .k_done(), .v_done(), .fault(), .ev_k_first(),
        .ev_v_first(), .req_valid(), .req_v(), .req_g(), .req_t(), .rsp_valid_in(1'b0), .rsp_data_in(1024'd0),
        .x_i(x_i), .x_o(), .rsv_i(rs_i[0]), .rsv_o(), .rvm_i(1'b0), .rvm_o(), .rsd_i(rs_i[512:1]), .rsd_o(),
        .t0_c(t0_cl[3:0]), .t1_c(t1_cl[3:0]), .t0_row(t0_row), .t1_row(t1_row), .t0_e(), .t1_e(), .t0_lt(t0_cl[15:4]),
        .t1_lt(t1_cl[15:4]), .t0_qv(), .t1_qv(), .t0_qb(), .t1_qb(), .t0_qd(), .t1_qd(), .ts0_sc(64'd0), .ts1_sc(64'd0),
        .ts0_sf(2'd0), .ts1_sf(2'd0), .ts0_gf(2'd0), .ts1_gf(2'd0));
endmodule

module qkd_ectl_c_tp8_direct #(parameter integer STATIC_QK=0, parameter integer QK_ISSUE_AGE=34, parameter integer ROW_RETURN_LAT=9, parameter integer HXK=0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    cfg,
    input  wire [633:0]  si,             // E: as qkd_ectl
    output wire [424:0]  so,             // E: as qkd_ectl
    output wire [15:0]   e0, e1, e2, e3, // S / N: e of head 0..3
    input  wire [33:0]   s0, s1, s2, s3, // S / N: {g_f, sc_f, sc 32} of head 0..3
    output wire [518:0]  t0_q,           // S / N: {q_data 512, q_beat 6, q_valid}
    output wire [518:0]  t1_q,
    input  wire          rsv_i,          // W: response valid directly from A stage 2
    output wire [51:0]   x_b,            // W: stage-2 control word to B (the same x2 register as x_a; r3)
    output wire [51:0]   x_a             // W: stage-2 control word directly to A
);
    ot_qkd_ectl_part #(.STATIC_QK(STATIC_QK), .QK_ISSUE_AGE(QK_ISSUE_AGE), .ROW_RETURN_LAT(ROW_RETURN_LAT), .HXK(HXK), .PART(3), .HEADS(1), .Q_FP32(1)) u (.clk(ck), .rst_n(rst_n), .cfg_s(cfg[1:0]), .cfg_e(cfg[4:2]),
        .start_in(si[0]), .T_in(si[14:1]), .cyc8_in(si[17:15]), .q_valid_in(si[18]), .q_beat_in(si[24:19]),
        .q_data_in(si[536:25]), .exp_done(si[568:537]), .er_data(si[632:569]), .nb_cr(si[633]),
        .er_valid(so[0]), .er_addr(so[12:1]), .sc_valid(so[13]), .sc_addr(so[25:14]), .sc_data(so[153:26]),
        .lmax(so[409:154]), .lmax_any(so[411:410]), .nb_valid(so[412]), .nb_beat(so[416:413]), .nb_g(so[417]),
        .nb_gam(so[421:418]), .k_done(so[422]), .v_done(so[423]), .fault(so[424]), .ev_k_first(), .ev_v_first(),
        .req_valid(), .req_v(), .req_g(), .req_t(), .rsp_valid_in(1'b0), .rsp_data_in(1024'd0),
        .x_i(52'd0), .x_o(), .x2_o(x_a), .rsv_i(rsv_i), .rsv_o(), .rvm_i(1'b0), .rvm_o(), .rsd_i(512'd0), .rsd_o(),
        .t0_c(), .t1_c(), .t0_row(), .t1_row(), .t0_e({e1, e0}), .t1_e({e3, e2}), .t0_lt(), .t1_lt(),
        .t0_qv(t0_q[0]), .t1_qv(t1_q[0]), .t0_qb(t0_q[6:1]), .t1_qb(t1_q[6:1]), .t0_qd(t0_q[518:7]), .t1_qd(t1_q[518:7]),
        .ts0_sc({s1[31:0], s0[31:0]}), .ts0_sf({s1[32], s0[32]}), .ts0_gf({s1[33], s0[33]}),
        .ts1_sc({s3[31:0], s2[31:0]}), .ts1_sf({s3[32], s2[32]}), .ts1_gf({s3[33], s2[33]}));
    assign x_b = x_a;                    // r3: B takes the stage-2 word too (C's x1 is a pure E-pin capture flop)
endmodule
