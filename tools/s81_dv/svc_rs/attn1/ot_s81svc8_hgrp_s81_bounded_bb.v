`timescale 1ns/1ps
// ATTN1 (10-20): BLACKBOX of the hard head group s81svc_attn_hgrp8 (top ot_s81svc8_hgrp_s81_bounded) for the
// narrowed attw parent's synthesis / native census before the hgrp8 view exists (ports = ot_s81svc8_hgrp_s81).
(* blackbox *)
module ot_s81svc8_hgrp_s81_bounded (
    input wire clk,
    input wire rst_n,
    input wire [7:0] gid,
    input wire ld_v,
    input wire ld_mode,
    input wire [2:0] ld_bank,
    input wire [7:0] ld_grp,
    input wire [2*32*16-1:0] ld_w,
    input wire [4*2*2*16-1:0] ld_wp,
    input wire ld_w2v,
    input wire iv,
    input wire [2:0] ibank,
    input wire [32*18-1:0] ib,
    output wire ov,
    output wire [4*32-1:0] oy,
    output wire [3:0] oflt
);
endmodule
