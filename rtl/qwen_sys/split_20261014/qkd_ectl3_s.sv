`timescale 1ns/1ps
// qwen-split/kvsys 2026-10-14 (owner 08:05 PT: no stubs): the row-engine control cell of the KV/system die as the
// hardened-once cluster of its three CLOSED leaves qkd_ectl_a | qkd_ectl_b | qkd_ectl_c (rtl/hdc/nearhbm/
// ot_qkd_ectl_parts.sv), wires only, with the die's ectl ports (si / so / t0 / t1 / e0..e3 / s0..s3 / rq / rs).  Identical
// to qkd_ectl3 except that the {engine, stack} index is a strap PORT (cfg, tied by the die per instance) instead of a
// parameter, so one master serves all 32 slots.  t[1558:0] = {q_data 512, q_beat 6, q_valid, lt 12, row 1024, c 4}.
// ck[0], ck[1], ck[2] are independently compensated entries for leaves A, B, C.
// This implementation still requires matching three-entry die clock/pin assignment.
module qkd_ectl3_s (
    input  wire [2:0]    ck,
    input  wire          rst_n,
    input  wire [4:0]    cfg,
    output wire [15:0]   e0, e1, e2, e3,
    input  wire [33:0]   s0, s1, s2, s3,
    output wire [1558:0] t0, t1,
    output wire [15:0]   rq,
    input  wire [1024:0] rs,
    input  wire [633:0]  si,
    output wire [424:0]  so
);
    wire [51:0]  x_cb, x_ba;
    wire [512:0] rs_ab;
    wire         rsv_bc, rvm_ab;
    wire [511:0] a0, a1, b0, b1;
    wire [15:0]  c0, c1;
    wire [518:0] q0, q1;
    qkd_ectl_a u_a (.ck(ck[0]), .rst_n(rst_n), .cfg(cfg), .rq(rq), .rs(rs), .t0_row(a0), .t1_row(a1), .x_i(x_ba), .rs_o(rs_ab), .rvm_o(rvm_ab));
    qkd_ectl_b u_b (.ck(ck[1]), .rst_n(rst_n), .cfg(cfg), .t0_row(b0), .t1_row(b1), .t0_cl(c0), .t1_cl(c1), .rs_i(rs_ab), .rvm_i(rvm_ab),
        .x_o(x_ba), .x_i(x_cb), .rsv_o(rsv_bc));
    qkd_ectl_c u_c (.ck(ck[2]), .rst_n(rst_n), .cfg(cfg), .si(si), .so(so), .e0(e0), .e1(e1), .e2(e2), .e3(e3), .s0(s0),
        .s1(s1), .s2(s2), .s3(s3), .t0_q(q0), .t1_q(q1), .rsv_i(rsv_bc), .x_o(x_cb));
    assign t0 = {q0[518:7], q0[6:1], q0[0], c0[15:4], b0, a0, c0[3:0]};
    assign t1 = {q1[518:7], q1[6:1], q1[0], c1[15:4], b1, a1, c1[3:0]};
endmodule
