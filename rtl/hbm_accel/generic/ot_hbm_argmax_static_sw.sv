`timescale 1ns/1ps
`default_nettype none
// SW-only source specialization: this die has slice ID zero.
// No runtime SID pin exists; synthesis specializes the real implementation.
// New master identity: historical dynamic-SID physical views do not qualify it.
module ot_hbm_argmax_static_sw #(
    parameter integer MUT = 0,
    parameter integer ACK = 12,
    parameter integer ELAT = 14      // measured: closed engine samples the last beat at L, out_v sampled at L+14
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    die_id,          // static rank strap
    input  wire          go,
    input  wire          mode,            // 0 VM, 1 STREAM
    input  wire [17:0]   imm_a,
    input  wire          a_mirror,
    input  wire [17:0]   a_base,
    input  wire [17:0]   n,
    input  wire [17:0]   o_base,
    input  wire [15:0]   o_is,
    output wire  [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    input  wire [522:0]  am_stream,       // {bias_en, bias256, vals256, mask8, last, v}
    output wire  [337:0]  cq,
    output wire  [1:0]    cq_seq,
    input  wire [273:0]  cr,
    output wire           busy, done, fault, nan_flag
);
 localparam [1:0] SID = 2'd0;
 ot_hbm_argmax_static #(.MUT(MUT),.ACK(ACK),.ELAT(ELAT)) implementation(.sid(SID), .*);
endmodule
`default_nettype wire
