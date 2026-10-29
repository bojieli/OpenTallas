`timescale 1ns/1ps
`default_nettype none
// Optional hardening master for the exact current S81 LP LN landing.
// The current bound parent connects ck_k and ck_n to the SAME clk. This
// wrapper preserves ck_k as the one physical clock entry and drops only ck_n.
// Independent timed reset inputs, all data/control pins and every cycle are
// preserved. No release parent selects this master without its plan event.
module ot_s81_mu72_lnland_nst_1ck #(
    parameter integer MUT = 0
) (
    input wire ck_k,
    input wire rs_k,
    input wire rs_n,
    input wire k_lo_v,
    input wire [552:0] k_lo_d,
    output wire k_lo_r,
    output wire k_li_v,
    output wire [552:0] k_li_d,
    input wire k_li_r,
    input wire k_rxv,
    output wire [2:0] k_flt,
    output wire n_lo_v,
    output wire [552:0] n_lo_d,
    input wire n_lo_r,
    input wire n_li_v,
    input wire [552:0] n_li_d,
    output wire n_li_r,
    output wire n_rxv,
    input wire [2:0] n_flt
);
    ot_s81_mu72_lnland_nst #(.MUT(MUT)) u_land (
        .ck_k(ck_k), .ck_n(ck_k), .rs_k(rs_k), .rs_n(rs_n),
        .k_lo_v(k_lo_v), .k_lo_d(k_lo_d), .k_lo_r(k_lo_r),
        .k_li_v(k_li_v), .k_li_d(k_li_d), .k_li_r(k_li_r),
        .k_rxv(k_rxv), .k_flt(k_flt),
        .n_lo_v(n_lo_v), .n_lo_d(n_lo_d), .n_lo_r(n_lo_r),
        .n_li_v(n_li_v), .n_li_d(n_li_d), .n_li_r(n_li_r),
        .n_rxv(n_rxv), .n_flt(n_flt)
    );
endmodule
`default_nettype wire
