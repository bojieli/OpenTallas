`timescale 1ns/1ps
// hgi-1010/g2 2026-10-10: the indexer's HARDENED ELEMENT = one 8-head chunk (ot_hdc_v41x_idx_chunk_l, generated, unchanged)
// with its head base as an input strap instead of a parameter, so ONE view serves all 4 chunks of a score engine (the
// L4 column tap = 4 chunk macros + ot_hdc_v41x_idx_tail_l + the line/beat front end; the flat 512-adder tap is not
// synthesizable: lane12 yosys OOM in `share`, lane8 11.5 h in synth -flatten).
// The chunk decodes a q-load head h as its local head h - HB (HB = 0 here): the element presents ql_head - hb, which lies in
// 0..7 exactly for heads hb..hb+7 (8-bit wrap; hb + 7 < 256), so every q-load, key beat and chunk sum is the chunk's own.
// hb is a die-level constant (0, 8, 16, 24); it reaches only the q-load head compare (a registered input of the chunk).
module ot_hdc_v41x_idx_chunk_el #(
    parameter integer NB  = 4,
    parameter integer NKT = 4,
    parameter integer FPL = 7,
    parameter integer FML = 5,
    parameter integer QL  = 5
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [7:0]            hb,
    input  wire                  ql_v,
    input  wire [7:0]            ql_head,
    input  wire [NB*128-1:0]     ql_codes,
    input  wire [NB*8-1:0]       ql_sc,
    input  wire [15:0]           ql_w,
    input  wire                  k_v,
    input  wire [NKT-1:0]        k_kv,
    input  wire [NKT*NB*136-1:0] k_key,
    output wire                  c_v,
    output wire [NKT-1:0]        c_kv,
    output wire [NKT*32-1:0]     c_sum,
    output wire [NKT-1:0]        c_fault
);
    ot_hdc_v41x_idx_chunk_l #(.NB(NB), .NKT(NKT), .HB(0), .FPL(FPL), .FML(FML), .QL(QL)) u_c (.clk(clk), .rst_n(rst_n),
        .ql_v(ql_v), .ql_head(ql_head - hb), .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w), .k_v(k_v), .k_kv(k_kv),
        .k_key(k_key), .c_v(c_v), .c_kv(c_kv), .c_sum(c_sum), .c_fault(c_fault));
endmodule
