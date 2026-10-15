`timescale 1ns/1ps
// el1011-hbm-idx 2026-10-11: blackbox of the hardened indexer slice (NB 4, FPL 7, FML 5, QL 5) for the hierarchical chunk
// top.  Read BEFORE ot_hdc_v41x_idx_chunk_el.sv: the define makes the chunk instantiate this macro (no parameters).
`define OT_IDX_HSLICE_HARD
(* blackbox *)
module ot_hdc_v41x_idx_hslice (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [7:0]   hid,
    input  wire         first,
    input  wire         ql_v,
    input  wire [7:0]   ql_head,
    input  wire [511:0] ql_codes,
    input  wire [31:0]  ql_sc,
    input  wire [15:0]  ql_w,
    output wire         qo_v,
    output wire [7:0]   qo_head,
    output wire [511:0] qo_codes,
    output wire [31:0]  qo_sc,
    output wire [15:0]  qo_w,
    input  wire [543:0] k_key,
    output wire [543:0] ko_key,
    input  wire [31:0]  cs_in,
    input  wire         cf_in,
    output wire [31:0]  cs_out,
    output wire         cf_out
);
endmodule
