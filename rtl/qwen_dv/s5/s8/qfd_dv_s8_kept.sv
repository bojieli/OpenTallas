`timescale 1ns/1ps
// QE3-SLICE2B 10-21: kept same-edge copies for the s8 slice parent (native census <=32 loads/driver).
// Every copy is a structural duplicate of an existing flop/gate at the SAME clock edge: no added cycles,
// no change of function. keep_hierarchy stops Yosys opt_merge from folding the copies back together.
`default_nettype none

// ---- RP1 write select: one kept arm copy + AND3 per <=12-bit vtw mux chunk.
(* keep_hierarchy = "yes" *)
module qfd_s8k_rp_wbit (input wire ck, rst, d, c519, c518, output wire w);
    (* keep = 1 *) reg arm;
    always @(posedge ck or negedge rst) if (!rst) arm <= 1'b0; else arm <= d;
    assign w = arm & c519 & c518;
endmodule

// N <= 24 arm copies with their own reset synchroniser (identical to rp1 u_rl: same rst_n, same 2-flop edge).
(* keep_hierarchy = "yes" *)
module qfd_s8k_rp_wgrp #(parameter integer N = 24) (
    input wire ck, rst_n, c_rpa, w_m, k7, arm_m,
    input wire [N-1:0] c519, c518,
    output wire [N-1:0] w
);
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    // == master rp_arm next state: if(c_rpa)1 else if(rp_w && rp_k==7)0 else hold
    wire nx = c_rpa | (arm_m & ~(w_m & k7));
    generate for (genvar c = 0; c < N; c = c + 1) begin : g_b
        (* keep_hierarchy = "yes" *) qfd_s8k_rp_wbit u_b (.ck(ck), .rst(rst), .d(nx), .c519(c519[c]), .c518(c518[c]), .w(w[c]));
    end endgenerate
endmodule

// ---- ARF1: kept c_xcc decode copies (go && op==0 && sub==0) and kept arf_fr AND copies.
(* keep_hierarchy = "yes" *)
module qfd_s8k_arf_dec (
    input wire c0, input wire [2:0] op, input wire [1:0] sub, input wire [3:0] dst, sid, input wire sid_ok,
    output wire c_xcc
);
    wire go = c0 && sid_ok && (dst == sid || dst == 4'hf) && op != 3'd7;
    assign c_xcc = go && op == 3'd0 && sub == 2'd0;
endmodule

(* keep_hierarchy = "yes" *)
module qfd_s8k_and2 (input wire a, b, output wire y);
    assign y = a & b;
endmodule

// ---- station fan-in split: the 4 shared rs_s/rs_n control bits leave as ONE net (one landing ring read by every
// station region) instead of being copied into each of the 8 per-region nets (8 rings x D slots on one input pin).
module qfd_dv_s8_frs (
    input  wire           ck,             // region membership only; no logic here
    input  wire [1027:0]  rs_s,
    output wire [127:0]   rs_s_r0, rs_s_r1, rs_s_r2, rs_s_r3, rs_s_r4, rs_s_r5, rs_s_r6, rs_s_r7,
    output wire [3:0]     rs_s_c
);
    assign rs_s_c  = {rs_s[1027:1026], rs_s[513:512]};
    assign rs_s_r0 = {rs_s[577:514], rs_s[63:0]};
    assign rs_s_r1 = {rs_s[641:578], rs_s[127:64]};
    assign rs_s_r2 = {rs_s[705:642], rs_s[191:128]};
    assign rs_s_r3 = {rs_s[769:706], rs_s[255:192]};
    assign rs_s_r4 = {rs_s[833:770], rs_s[319:256]};
    assign rs_s_r5 = {rs_s[897:834], rs_s[383:320]};
    assign rs_s_r6 = {rs_s[961:898], rs_s[447:384]};
    assign rs_s_r7 = {rs_s[1025:962], rs_s[511:448]};
endmodule

module qfd_dv_s8_fn (
    input  wire           ck,             // region membership only; no logic here
    input  wire [1027:0]  rs_n,
    output wire [127:0]   rs_n_r0, rs_n_r1, rs_n_r2, rs_n_r3, rs_n_r4, rs_n_r5, rs_n_r6, rs_n_r7,
    output wire [3:0]     rs_n_c
);
    assign rs_n_c  = {rs_n[1027:1026], rs_n[513:512]};
    assign rs_n_r0 = {rs_n[577:514], rs_n[63:0]};
    assign rs_n_r1 = {rs_n[641:578], rs_n[127:64]};
    assign rs_n_r2 = {rs_n[705:642], rs_n[191:128]};
    assign rs_n_r3 = {rs_n[769:706], rs_n[255:192]};
    assign rs_n_r4 = {rs_n[833:770], rs_n[319:256]};
    assign rs_n_r5 = {rs_n[897:834], rs_n[383:320]};
    assign rs_n_r6 = {rs_n[961:898], rs_n[447:384]};
    assign rs_n_r7 = {rs_n[1025:962], rs_n[511:448]};
endmodule
`default_nettype wire
