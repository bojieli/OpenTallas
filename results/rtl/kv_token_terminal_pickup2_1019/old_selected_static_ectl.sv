`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// RTL-BUILD-KV/ASTK 2026-10-18 (lanes/RTL-BUILD-KV.md P4 / F5; KVE-2-ASTK note for KVJ-D): the static ECTL frame on the
// credit-free ASTK ABI.
//
//   qkd_ectl_c_st     = qkd_ectl_c_tp8_direct (STATIC_QK) without the node credit input nb_cr (old si[633]) and without
//                       the node-beat / done outputs so[423:412] {v_done, k_done, nb_gam 4, nb_g, nb_beat 4, nb_valid}.
//                       si = si[632:0] (633 b), so = {fault, so[411:0]} (413 b) -- the ABI of qkd_astk_strip_st /
//                       qkd_astk_strip_er_st.  Logic and edges are otherwise the C leaf's: with STATIC_QK the engine
//                       finishes at the end of its K pass (no V phase: P.V runs in the pvw pairs), so pend / offer / take
//                       never fire, the local P.V tree decision word ltw is constant 0, ob_send never fires and the node
//                       beats are constant 0; the credit counter ocred (x[50]) only gated ob_send.  nb_cr enters the
//                       control word as 0 (what the current strip's EP drives: qkd_astk_ep_cal si[633] = cr_q = cr = 0),
//                       so the x seam to A / B is the unchanged 52-b word (A = the CRITICAL qkd_static_ectla_kiss and B
//                       keep their closed pins; x[50] is a constant-0 launch the synthesis of C keeps or folds).
//   qkd_ectl3_kiss_st = qkd_ectl3_kiss_s with C replaced by qkd_ectl_c_st (A + K issuer and B unchanged).
//
// K-15 (rvm_i = 0 in A / B / C): the direct-seam leaves feed rsp_valid A rv2 -> B / C rsv_i directly (r3); rvm_i only
// loads the legacy feed-through flop bf, whose output rsv_o is used for PART 2/3 only and is unconnected in every direct
// leaf (and A's rvm_o is unconnected).  It is dead legacy logic of the shared ot_qkd_ectl_part, not a mode strap and not a
// functional input: tying it here is a constant on an unobservable cone (synthesis removes rvm / bf).
// Mutants (`KVD_ECSTMUT): 1 = so fault bit taken from k_done; 2 = q word taken one si bit low (si[536:25] -> {si[535:25], 0}).
// Bench: rtl/test/qwen_static_kv/tb_qkd_ectl3_kiss_st.sv (lockstep vs qkd_ectl3_kiss_s on the static K stimulus).
// ---------------------------------------------------------------------------------------------------------------------
// leaf: qkd_ectl_c_st.sv

module qkd_ectl3_kiss_st #(parameter integer RESPONSE_LAT=14, parameter integer QK_ISSUE_AGE=34, parameter integer HXK=0, parameter integer MUT=0) (
    input  wire [2:0]    ck, input wire rst_n, input wire [4:0] cfg,
    output wire [15:0]   e0, e1, e2, e3, input wire [33:0] s0, s1, s2, s3,
    output wire [1558:0] t0, t1,
    input  wire          kgo, input wire [15:0] epoch, input wire [5:0] layer,
    output wire          req_valid, output wire [13:0] req_t, output wire req_v,
    output wire [15:0]   req_epoch, output wire [5:0] req_layer,
    input  wire          rsp_valid, input wire [1023:0] rsp_data, input wire [13:0] rsp_t,
    input  wire          rsp_v, input wire [15:0] rsp_epoch, input wire [5:0] rsp_layer,
    output wire          fault,
    input  wire [632:0]  si, output wire [412:0] so
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
    qkd_ectl_c_st #(.QK_ISSUE_AGE(QK_ISSUE_AGE), .ROW_RETURN_LAT(RRL), .HXK(HXK)) u_c (.ck(ck[2]), .rst_n(rst_n), .cfg(cfg), .si(si), .so(so), .e0(e0), .e1(e1), .e2(e2), .e3(e3), .s0(s0),
        .s1(s1), .s2(s2), .s3(s3), .t0_q(q0), .t1_q(q1), .rsv_i(rs_ab[0]), .x_b(x_cb), .x_a(x_ca));
    assign t0 = {q0[518:7], q0[6:1], q0[0], c0[15:4], b0, a0, c0[3:0]};
    assign t1 = {q1[518:7], q1[6:1], q1[0], c1[15:4], b1, a1, c1[3:0]};
endmodule
