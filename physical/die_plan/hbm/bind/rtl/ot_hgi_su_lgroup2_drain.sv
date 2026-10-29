`timescale 1ns/1ps
`default_nettype none
// HBM-BIND-3 (2026-10-29, COORD ruling b): drain-only form of ot_hgi_su_lgroup2 for the SFU operand-store output
// group (ot_hgi_sfu_static_operand_store u_output: NS=2 sector drain reads + NLW=16 lane writes).  The parent ties the
// lane read port (rq/rr/ra; rd unread), the sector stage-write port (sw_v/sw_addr/sw_mask/sw_d) and the single-word
// landing (s1_v/s1_a/s1_d) to literal zeros.  This variant removes those ports from the interface and applies the
// SAME constants inside, so the drain/lane-write behaviour (sr_d, sr_rv, flt) is identical cycle for cycle
// (cycle-exact lockstep: results/hbm_bind_3_1029/lgroup2_drain).  Synthesis removes the dead read/stage logic.
// Ports are a subset of ot_hgi_su_lgroup2 (bind substitute_inst; the removed inputs are declared port_bit_constants).
module ot_hgi_su_lgroup2_drain #(
    parameter integer N = 16, M = 8, LWB = 17, AW = 24,
    parameter integer NLW = 0,
    parameter integer MACRO = 1,
    parameter integer MUT_XBAR = 0,
    parameter integer LAT = 0,
    parameter integer NS = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NS-1:0]     sr_v,
    input  wire [NS*LWB-1:0] sr_addr,
    output wire [NS*256-1:0] sr_d,
    output wire [NS-1:0]     sr_rv,
    input  wire [(NLW>0?NLW:1)-1:0]    lw,
    input  wire [(NLW>0?NLW:1)*AW-1:0] lwa,
    input  wire [(NLW>0?NLW:1)*32-1:0] lwd,
    output wire              flt
);
    wire [N*32-1:0] rd_unused;
    ot_hgi_su_lgroup2 #(.N(N), .M(M), .LWB(LWB), .AW(AW), .NLW(NLW), .MACRO(MACRO), .MUT_XBAR(MUT_XBAR), .LAT(LAT),
        .NS(NS)) u_g (
        .clk(clk), .rst_n(rst_n), .rq({N{1'b0}}), .rr({N{1'b0}}), .ra({N*AW{1'b0}}), .rd(rd_unused),
        .sr_v(sr_v), .sr_addr(sr_addr), .sr_d(sr_d), .sr_rv(sr_rv),
        .sw_v({NS{1'b0}}), .sw_addr({NS*LWB{1'b0}}), .sw_mask({NS*8{1'b0}}), .sw_d({NS*256{1'b0}}),
        .lw(lw), .lwa(lwa), .lwd(lwd), .s1_v(1'b0), .s1_a({LWB{1'b0}}), .s1_d(32'd0), .flt(flt));
endmodule
`default_nettype wire
