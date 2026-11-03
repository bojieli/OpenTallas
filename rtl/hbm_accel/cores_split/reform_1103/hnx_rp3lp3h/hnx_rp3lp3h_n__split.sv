`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-61/SPLIT 11-03: split composition of hnx_rp3lp3h_n (same ports as the kit core, face-shelled form): the sub-blocks of
// hnx_rp3h_split.sv instantiated in their face-shelled form (<sub>__fs = reform_1103/facewrap.py model of the kit face
// shell), so this module is cycle-exact with the hardened composition.  Leaf result +7 edges (see hnx_rp3h_split.sv).
module hnx_rp3lp3h_n__split #(parameter integer MUT = 0) (
    input wire ck_n, input wire rst_n,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [817:0] rin_n, input wire [2068:0] bin, input wire [99:0] gin,
    output wire [817:0] rout_n, output wire [2068:0] bout, output wire [599:0] sb_bank, output wire [3:0] sb_vld);
    wire rst_lf; wire [25:0] lf_st; wire [817:0] lf_rl1; wire [2068:0] lf_bk1;
    wire [2:0] act; wire [12:0] rr; wire [3*1102-1:0] lc_op; wire [6*258-1:0] tl_op; wire [149:0] lg;
    hnx_rp3h_xs__fs u_xs (.clk(ck_n), .rst_lf(rst_lf), .st(lf_st), .rl1(lf_rl1), .bk1(lf_bk1), .act(act), .rst_ln(rr), .lc_op(lc_op), .tl_op(tl_op));
    genvar p;
    generate for (p = 0; p < 3; p = p + 1) begin : g_ln
        wire [255:0] s0, s1; wire l0, l1;
        hnx_rp3h_tl__fs u_tl0 (.clk(ck_n), .rst_tcc(rr[2+4*p]), .op(tl_op[(2*p)*258 +: 258]), .sum_o(s0), .lfault(l0));
        hnx_rp3h_tl__fs u_tl1 (.clk(ck_n), .rst_tcc(rr[2+4*p]), .op(tl_op[(2*p+1)*258 +: 258]), .sum_o(s1), .lfault(l1));
        hnx_rp3h_lc__fs #(.MUT(MUT)) u_lc (.clk(ck_n), .rst_bdc(rr[1+4*p]), .rst_tcc(rr[2+4*p]), .rst_g(rr[3+4*p]), .rst_x(rr[4+4*p]),
            .op(lc_op[p*1102 +: 1102]), .sum0(s0), .sum1(s1), .lf0(l0), .lf1(l1), .g(lg[p*50 +: 50]));
    end endgenerate
    hnx_rp3h_gn__fs #(.MUT(MUT)) u_g (.ck_n(ck_n), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
        .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout), .sb_bank(sb_bank), .sb_vld(sb_vld),
        .rst_lf(rst_lf), .lf_st(lf_st), .lf_rl1(lf_rl1), .lf_bk1(lf_bk1), .lf_act(act), .lf_g(lg));
endmodule
`default_nettype wire
