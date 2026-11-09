`timescale 1ns/1ps
// --------------------------------------------------------------------------------------------------------------------
// ot_qfd_xs_leaf_fo32_w (QC-TYPES-10/HC3 2026-11-08): plan-variant wrapper so the die bind can substitute the
// native-census leaf ot_qfd_xs_leaf_fo32 for an as-built ot_qfd_xs_leaf #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))
// instance (asbuilt substitute_inst).  It declares the as-built parameters (fo32 has NCH as a localparam, so a bound
// #(.NCH(4)) on fo32 itself would not elaborate) and accepts ONLY the configuration fo32 is cycle-exact against
// (tb_qfd_xs_leaf_fo32): NCH 4, READ_PIN_PIPE 1, FILL_PIPE 1, BANK_PIPE 0, EXTERNAL_WD_CAPTURE 0.  Any other value
// stops elaboration.  Pure pass-through: no logic, no added edge.
// --------------------------------------------------------------------------------------------------------------------
module ot_qfd_xs_leaf_fo32_w #(
    parameter integer EXTERNAL_WD_CAPTURE = 0,
    parameter integer FILL_PIPE = 1,
    parameter integer READ_PIN_PIPE = 1,
    parameter integer BANK_PIPE = 0,
    parameter integer NCH = 4,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          w_v,
    input  wire          w_ep,
    input  wire [5:0]    w_off,
    input  wire [63:0]   w_m,
    input  wire [1023:0] w_d,
    input  wire [NCH*18-1:0] w_ctl,
    input  wire          c_v,
    input  wire          c_ep,
    output wire          wo_v,
    output wire          wo_ep,
    output wire [5:0]    wo_off,
    output wire [63:0]   wo_m,
    output wire [1023:0] wo_d,
    output wire [NCH*18-1:0] wo_ctl,
    output wire          co_v,
    output wire          co_ep,
    input  wire          r_v,
    input  wire          r_t,
    input  wire          r_ep,
    input  wire [27:0]   r_p,
    output wire          q_v,
    output wire [63:0]   q,
    output wire          q_bad
);
    generate if (NCH != 4 || FILL_PIPE != 1 || READ_PIN_PIPE != 1 || BANK_PIPE != 0 || EXTERNAL_WD_CAPTURE != 0)
    begin : g_cfg_mismatch
        $error("ot_qfd_xs_leaf_fo32_w: only NCH 4 / FILL_PIPE 1 / READ_PIN_PIPE 1 / BANK_PIPE 0 / EXTERNAL_WD_CAPTURE 0");
    end endgenerate
    ot_qfd_xs_leaf_fo32 #(.MUT(MUT)) u_leaf (
        .clk(clk), .rst_n(rst_n), .w_v(w_v), .w_ep(w_ep), .w_off(w_off), .w_m(w_m), .w_d(w_d), .w_ctl(w_ctl),
        .c_v(c_v), .c_ep(c_ep), .wo_v(wo_v), .wo_ep(wo_ep), .wo_off(wo_off), .wo_m(wo_m), .wo_d(wo_d), .wo_ctl(wo_ctl),
        .co_v(co_v), .co_ep(co_ep), .r_v(r_v), .r_t(r_t), .r_ep(r_ep), .r_p(r_p), .q_v(q_v), .q(q), .q_bad(q_bad));
endmodule
