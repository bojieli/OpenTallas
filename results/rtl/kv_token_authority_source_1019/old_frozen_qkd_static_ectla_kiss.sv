`timescale 1ns/1ps
// KVJ-D 2026-10-17 (kv_static_join_plan item 7): ECTL A with its static K issuer folded in as one tile.
// The 1:1 issuer <-> ECTL A pair (validate_native_edges) becomes internal nets; the separate 1-Kb rq/rs tile hop
// is removed.  Both children are the unchanged ROLES RTL: the ECTL A body is instanced exactly as
// qkd_ectl_a_tp8_epoch_direct does (EPOCH 1, instance name u, so u.u is the direct engine), and the issuer is
// qkd_static_k_issuer.  ROW_RETURN_LAT = RESPONSE_LAT + 7 is enforced here (the issuer's 2 registered edges,
// the internal net and ECTL's own rs capture count inside the RTL constants; no cycle is added or removed
// relative to the two-tile composition).  W face = the landing segment's K request / response; S = control.
module qkd_static_ectla_kiss #(parameter integer RESPONSE_LAT=14, parameter integer QK_ISSUE_AGE=34,
                               parameter integer HXK=13, parameter integer MUT=0) (
    input  wire          ck, rst_n,
    input  wire [4:0]    cfg,
    input  wire          kgo, input wire [15:0] epoch, input wire [5:0] layer,
    output wire          req_valid, output wire [13:0] req_t, output wire req_v,
    output wire [15:0]   req_epoch, output wire [5:0] req_layer,
    input  wire          rsp_valid, input wire [1023:0] rsp_data, input wire [13:0] rsp_t,
    input  wire          rsp_v, input wire [15:0] rsp_epoch, input wire [5:0] rsp_layer,
    output wire [511:0]  t0_row, t1_row,
    input  wire [51:0]   x_i, output wire [512:0] rs_o,
    output wire          fault
);
    wire [16:0]   rq;
    wire [1024:0] rs;
    qkd_ectl_a_tp8_direct #(.EPOCH(1), .STATIC_QK(1), .QK_ISSUE_AGE(QK_ISSUE_AGE), .ROW_RETURN_LAT(RESPONSE_LAT+7), .HXK(HXK)) u (
        .ck(ck), .rst_n(rst_n), .cfg(cfg), .rq(rq), .rs(rs), .t0_row(t0_row), .t1_row(t1_row), .x_i(x_i), .rs_o(rs_o));
    qkd_static_k_issuer #(.RESPONSE_LAT(RESPONSE_LAT), .MUT(MUT)) u_k (
        .ck(ck), .rst_n(rst_n), .kgo(kgo), .epoch(epoch), .layer(layer), .rq(rq),
        .req_valid(req_valid), .req_t(req_t), .req_v(req_v), .req_epoch(req_epoch), .req_layer(req_layer),
        .rsp_valid(rsp_valid), .rsp_data(rsp_data), .rsp_t(rsp_t), .rsp_v(rsp_v), .rsp_epoch(rsp_epoch), .rsp_layer(rsp_layer),
        .rs(rs), .fault(fault));
endmodule

// Bench / die composition parent: qkd_ectl3_epoch_direct_s with leaf A replaced by the fused A + issuer tile.
module qkd_ectl3_kiss_s #(parameter integer RESPONSE_LAT=14, parameter integer QK_ISSUE_AGE=34, parameter integer HXK=0, parameter integer MUT=0) (
    input  wire [2:0]    ck, input wire rst_n, input wire [4:0] cfg,
    output wire [15:0]   e0, e1, e2, e3, input wire [33:0] s0, s1, s2, s3,
    output wire [1558:0] t0, t1,
    input  wire          kgo, input wire [15:0] epoch, input wire [5:0] layer,
    output wire          req_valid, output wire [13:0] req_t, output wire req_v,
    output wire [15:0]   req_epoch, output wire [5:0] req_layer,
    input  wire          rsp_valid, input wire [1023:0] rsp_data, input wire [13:0] rsp_t,
    input  wire          rsp_v, input wire [15:0] rsp_epoch, input wire [5:0] rsp_layer,
    output wire          fault,
    input  wire [633:0]  si, output wire [424:0] so
);
    localparam integer RRL = RESPONSE_LAT + 7;
    wire [51:0]  x_cb, x_ca; wire [512:0] rs_ab;
    wire [511:0] a0, a1, b0, b1; wire [15:0] c0, c1; wire [518:0] q0, q1;
    qkd_static_ectla_kiss #(.RESPONSE_LAT(RESPONSE_LAT), .QK_ISSUE_AGE(QK_ISSUE_AGE), .HXK(HXK), .MUT(MUT)) u_a (
        .ck(ck[0]), .rst_n(rst_n), .cfg(cfg), .kgo(kgo), .epoch(epoch), .layer(layer),
        .req_valid(req_valid), .req_t(req_t), .req_v(req_v), .req_epoch(req_epoch), .req_layer(req_layer),
        .rsp_valid(rsp_valid), .rsp_data(rsp_data), .rsp_t(rsp_t), .rsp_v(rsp_v), .rsp_epoch(rsp_epoch), .rsp_layer(rsp_layer),
        .t0_row(a0), .t1_row(a1), .x_i(x_ca), .rs_o(rs_ab), .fault(fault));
    qkd_ectl_b_tp8_direct #(.STATIC_QK(1), .QK_ISSUE_AGE(QK_ISSUE_AGE), .ROW_RETURN_LAT(RRL), .HXK(HXK)) u_b (.ck(ck[1]), .rst_n(rst_n), .cfg(cfg), .t0_row(b0), .t1_row(b1), .t0_cl(c0), .t1_cl(c1), .rs_i(rs_ab), .x_i(x_cb));
    qkd_ectl_c_tp8_direct #(.STATIC_QK(1), .QK_ISSUE_AGE(QK_ISSUE_AGE), .ROW_RETURN_LAT(RRL), .HXK(HXK)) u_c (.ck(ck[2]), .rst_n(rst_n), .cfg(cfg), .si(si), .so(so), .e0(e0), .e1(e1), .e2(e2), .e3(e3), .s0(s0),
        .s1(s1), .s2(s2), .s3(s3), .t0_q(q0), .t1_q(q1), .rsv_i(rs_ab[0]), .x_b(x_cb), .x_a(x_ca));
    assign t0 = {q0[518:7], q0[6:1], q0[0], c0[15:4], b0, a0, c0[3:0]};
    assign t1 = {q1[518:7], q1[6:1], q1[0], c1[15:4], b1, a1, c1[3:0]};
endmodule
